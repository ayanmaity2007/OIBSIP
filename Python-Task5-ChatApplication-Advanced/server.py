"""Threaded multi-room chat server with SQLite authentication and history."""

import argparse
import datetime as dt
import os
import socket
import sqlite3
import threading
from typing import Any, Dict, List, Optional, Set

from common import (
    HOST,
    PORT,
    hash_password,
    receive_json,
    render_shortcodes,
    send_json,
    timestamp,
    valid_room_name,
    valid_username,
    verify_password,
)


class DatabaseError(Exception):
    """Raised for a chat database failure."""


class ChatDatabase:
    """SQLite repository for users, rooms, and messages.

    A short-lived connection is used for each operation. This avoids sharing a
    SQLite connection across client threads and makes the server safer to
    scale to several simultaneous clients.
    """

    def __init__(self, path: str) -> None:
        self.path = path
        self.write_lock = threading.Lock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        try:
            with self._connect() as connection:
                connection.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                        password_salt TEXT NOT NULL,
                        password_digest TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS rooms (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL UNIQUE COLLATE NOCASE,
                        created_at TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        room_id INTEGER NOT NULL,
                        username TEXT NOT NULL,
                        body TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE CASCADE
                    );
                    CREATE INDEX IF NOT EXISTS idx_messages_room_id ON messages(room_id, id);
                    """
                )
                connection.execute(
                    "INSERT OR IGNORE INTO rooms (name, created_at) VALUES (?, ?)",
                    ("Lobby", dt.datetime.now().isoformat(timespec="seconds")),
                )
        except sqlite3.Error as error:
            raise DatabaseError("Could not initialise chat database: {}".format(error))

    def register(self, username: str, password: str) -> None:
        """Create a user with a salted PBKDF2 password hash."""
        if not valid_username(username):
            raise ValueError("Username must be 3–24 letters, numbers, or underscores.")
        if len(password) < 8:
            raise ValueError("Password must contain at least 8 characters.")
        credentials = hash_password(password)
        try:
            with self.write_lock:
                with self._connect() as connection:
                    connection.execute(
                        """
                        INSERT INTO users (username, password_salt, password_digest, created_at)
                        VALUES (?, ?, ?, ?)
                        """,
                        (
                            username.strip(),
                            credentials["salt"],
                            credentials["digest"],
                            dt.datetime.now().isoformat(timespec="seconds"),
                        ),
                    )
        except sqlite3.IntegrityError:
            raise ValueError("That username is already registered.")
        except sqlite3.Error as error:
            raise DatabaseError("Could not register the user: {}".format(error))

    def authenticate(self, username: str, password: str) -> bool:
        """Verify username and password without returning password data."""
        try:
            with self._connect() as connection:
                row = connection.execute(
                    "SELECT username, password_salt, password_digest FROM users WHERE username = ?",
                    (username.strip(),),
                ).fetchone()
        except sqlite3.Error as error:
            raise DatabaseError("Could not authenticate the user: {}".format(error))
        return bool(row and verify_password(password, row["password_salt"], row["password_digest"]))

    def create_room(self, name: str) -> None:
        """Create a named room if it does not already exist."""
        name = name.strip()
        if not valid_room_name(name):
            raise ValueError("Room names must be 1–32 letters, numbers, spaces, _ or -.")
        try:
            with self.write_lock:
                with self._connect() as connection:
                    connection.execute(
                        "INSERT INTO rooms (name, created_at) VALUES (?, ?)",
                        (name, dt.datetime.now().isoformat(timespec="seconds")),
                    )
        except sqlite3.IntegrityError:
            raise ValueError("That room already exists.")
        except sqlite3.Error as error:
            raise DatabaseError("Could not create the room: {}".format(error))

    def list_rooms(self) -> List[str]:
        """Return all room names."""
        try:
            with self._connect() as connection:
                rows = connection.execute("SELECT name FROM rooms ORDER BY name COLLATE NOCASE").fetchall()
            return [str(row["name"]) for row in rows]
        except sqlite3.Error as error:
            raise DatabaseError("Could not list rooms: {}".format(error))

    def room_exists(self, name: str) -> bool:
        """Check a room name using a parameterised query."""
        try:
            with self._connect() as connection:
                row = connection.execute("SELECT 1 FROM rooms WHERE name = ?", (name,)).fetchone()
            return row is not None
        except sqlite3.Error as error:
            raise DatabaseError("Could not find the room: {}".format(error))

    def save_message(self, room: str, username: str, body: str) -> str:
        """Store one rendered message and return its display timestamp."""
        stamp = timestamp()
        try:
            with self.write_lock:
                with self._connect() as connection:
                    room_row = connection.execute("SELECT id FROM rooms WHERE name = ?", (room,)).fetchone()
                    if not room_row:
                        raise ValueError("That room no longer exists.")
                    connection.execute(
                        """
                        INSERT INTO messages (room_id, username, body, created_at)
                        VALUES (?, ?, ?, ?)
                        """,
                        (room_row["id"], username, render_shortcodes(body), stamp),
                    )
            return stamp
        except ValueError:
            raise
        except sqlite3.Error as error:
            raise DatabaseError("Could not save the message: {}".format(error))

    def history(self, room: str, limit: int = 100) -> List[Dict[str, str]]:
        """Return the latest messages in chronological order."""
        try:
            with self._connect() as connection:
                room_row = connection.execute("SELECT id FROM rooms WHERE name = ?", (room,)).fetchone()
                if not room_row:
                    raise ValueError("That room does not exist.")
                rows = connection.execute(
                    """
                    SELECT username, body, created_at
                    FROM messages
                    WHERE room_id = ?
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (room_row["id"], max(1, min(limit, 500))),
                ).fetchall()
            return [
                {"username": row["username"], "message": row["body"], "timestamp": row["created_at"]}
                for row in reversed(rows)
            ]
        except ValueError:
            raise
        except sqlite3.Error as error:
            raise DatabaseError("Could not read message history: {}".format(error))


class ClientSession:
    """State and serialised writes for one connected client."""

    def __init__(self, connection: socket.socket, address: Any) -> None:
        self.connection = connection
        self.address = address
        self.send_lock = threading.Lock()
        self.username: Optional[str] = None
        self.room: Optional[str] = None

    @property
    def authenticated(self) -> bool:
        return self.username is not None

    def send(self, payload: Dict[str, Any]) -> None:
        """Send safely even when broadcasts occur from multiple threads."""
        with self.send_lock:
            send_json(self.connection, payload)


class ChatServer:
    """Thread-per-client TCP server supporting rooms and persisted history."""

    def __init__(self, host: str, port: int, database_path: str) -> None:
        self.host = host
        self.port = port
        self.database = ChatDatabase(database_path)
        self.server_socket: Optional[socket.socket] = None
        self.clients: Dict[socket.socket, ClientSession] = {}
        self.lock = threading.RLock()
        self.running = False

    def start(self) -> None:
        """Bind, listen, and serve clients until interrupted."""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(20)
        self.running = True
        print("Chat server listening on {}:{}".format(self.host, self.port))
        try:
            while self.running:
                connection, address = self.server_socket.accept()
                connection.settimeout(None)
                session = ClientSession(connection, address)
                with self.lock:
                    self.clients[connection] = session
                threading.Thread(target=self._client_loop, args=(session,), daemon=True).start()
        except OSError:
            if self.running:
                raise
        finally:
            self.stop()

    def stop(self) -> None:
        """Close the listener and all active client sockets."""
        self.running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except OSError:
                pass
        with self.lock:
            sessions = list(self.clients.values())
            self.clients.clear()
        for session in sessions:
            try:
                session.connection.close()
            except OSError:
                pass

    def _client_loop(self, session: ClientSession) -> None:
        """Read and dispatch requests from one client."""
        try:
            while self.running:
                request = receive_json(session.connection)
                self._handle_request(session, request)
        except (ConnectionError, OSError, ValueError):
            pass
        finally:
            self._disconnect(session)

    def _reply(self, session: ClientSession, action: str, ok: bool, message: str, **extra: Any) -> None:
        payload: Dict[str, Any] = {"type": "response", "action": action, "ok": ok, "message": message}
        payload.update(extra)
        try:
            session.send(payload)
        except (OSError, ValueError):
            self._disconnect(session)

    def _handle_request(self, session: ClientSession, request: Dict[str, Any]) -> None:
        action = str(request.get("action", ""))
        if action == "register":
            try:
                self.database.register(str(request.get("username", "")), str(request.get("password", "")))
                self._reply(session, action, True, "Registration successful. You can now log in.")
            except (ValueError, DatabaseError) as error:
                self._reply(session, action, False, str(error))
            return

        if action == "login":
            if session.authenticated:
                self._reply(session, action, False, "This connection is already logged in.")
                return
            username = str(request.get("username", "")).strip()
            password = str(request.get("password", ""))
            try:
                valid = self.database.authenticate(username, password)
            except DatabaseError as error:
                self._reply(session, action, False, str(error))
                return
            if not valid:
                self._reply(session, action, False, "Invalid username or password.")
                return
            with self.lock:
                already_online = any(
                    other is not session and other.username and other.username.lower() == username.lower()
                    for other in self.clients.values()
                )
            if already_online:
                self._reply(session, action, False, "That user is already connected.")
                return
            session.username = username
            try:
                rooms = self.database.list_rooms()
            except DatabaseError as error:
                session.username = None
                self._reply(session, action, False, str(error))
                return
            self._reply(session, action, True, "Login successful.", username=username, rooms=rooms)
            return

        if not session.authenticated:
            self._reply(session, action, False, "Please log in first.")
            return

        try:
            if action == "list_rooms":
                self._reply(session, action, True, "Rooms loaded.", rooms=self.database.list_rooms())
            elif action == "create_room":
                room = str(request.get("room", "")).strip()
                self.database.create_room(room)
                self._reply(session, action, True, "Room created.", room=room, rooms=self.database.list_rooms())
            elif action == "join_room":
                self._join_room(session, str(request.get("room", "")).strip())
            elif action == "leave_room":
                self._leave_room(session, announce=True)
                self._reply(session, action, True, "You left the room.")
            elif action == "send_message":
                self._send_message(session, str(request.get("message", "")))
            elif action == "logout":
                self._leave_room(session, announce=True)
                session.username = None
                self._reply(session, action, True, "Logged out.")
            else:
                self._reply(session, action, False, "Unknown action.")
        except (ValueError, DatabaseError) as error:
            self._reply(session, action, False, str(error))

    def _join_room(self, session: ClientSession, room: str) -> None:
        if not self.database.room_exists(room):
            raise ValueError("That room does not exist.")
        if session.room == room:
            history = self.database.history(room)
            self._reply(session, "join_room", True, "You are already in {}.".format(room), room=room, history=history)
            return
        old_room = session.room
        if old_room:
            self._leave_room(session, announce=True)
        history = self.database.history(room)
        with self.lock:
            session.room = room
        self._reply(session, "join_room", True, "Joined {}.".format(room), room=room, history=history)
        self._broadcast_room(
            room,
            {
                "type": "system",
                "room": room,
                "message": "{} joined the room.".format(session.username),
                "timestamp": timestamp(),
            },
            exclude=session,
        )

    def _leave_room(self, session: ClientSession, announce: bool) -> None:
        room = session.room
        if not room:
            return
        with self.lock:
            session.room = None
        if announce:
            self._broadcast_room(
                room,
                {
                    "type": "system",
                    "room": room,
                    "message": "{} left the room.".format(session.username),
                    "timestamp": timestamp(),
                },
                exclude=session,
            )

    def _send_message(self, session: ClientSession, body: str) -> None:
        body = body.strip()
        if not session.room:
            raise ValueError("Join a room before sending a message.")
        if not body:
            raise ValueError("Message cannot be empty.")
        if len(body) > 2000:
            raise ValueError("Message cannot exceed 2,000 characters.")
        stamp = self.database.save_message(session.room, session.username or "", body)
        self._broadcast_room(
            session.room,
            {
                "type": "message",
                "room": session.room,
                "username": session.username,
                "message": render_shortcodes(body),
                "timestamp": stamp,
            },
        )

    def _broadcast_room(self, room: str, payload: Dict[str, Any], exclude: Optional[ClientSession] = None) -> None:
        with self.lock:
            recipients = [session for session in self.clients.values() if session.room == room and session is not exclude]
        for recipient in recipients:
            try:
                recipient.send(payload)
            except (OSError, ValueError):
                self._disconnect(recipient)

    def _disconnect(self, session: ClientSession) -> None:
        room = session.room
        username = session.username
        self._leave_room(session, announce=False)
        with self.lock:
            self.clients.pop(session.connection, None)
        try:
            session.connection.close()
        except OSError:
            pass
        if room and username:
            self._broadcast_room(
                room,
                {
                    "type": "system",
                    "room": room,
                    "message": "{} disconnected.".format(username),
                    "timestamp": timestamp(),
                },
            )


def main() -> None:
    """Read server options and start the socket server."""
    parser = argparse.ArgumentParser(description="Advanced multi-room chat server")
    parser.add_argument("--host", default=os.getenv("CHAT_HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.getenv("CHAT_PORT", str(PORT))))
    parser.add_argument("--database", default=os.getenv("CHAT_DATABASE", "chat.db"))
    args = parser.parse_args()
    server = ChatServer(args.host, args.port, args.database)
    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()
        print("\nChat server stopped.")


if __name__ == "__main__":
    main()
