"""Tkinter GUI client for the advanced multi-room chat server."""

import queue
import socket
import threading
import tkinter as tk
from tkinter import ttk
from typing import Any, Dict, List, Optional

from common import HOST, PORT, receive_json, render_shortcodes, send_json


class NetworkClient:
    """Length-prefixed JSON socket client with a background reader thread."""

    def __init__(self, events: "queue.Queue[Dict[str, Any]]") -> None:
        self.events = events
        self.connection: Optional[socket.socket] = None
        self.send_lock = threading.Lock()
        self.closed = True

    def connect(self, host: str, port: int) -> None:
        """Connect to the server and begin receiving events."""
        self.close()
        self.connection = socket.create_connection((host, port), timeout=6)
        self.connection.settimeout(None)
        self.closed = False
        threading.Thread(target=self._reader, daemon=True).start()

    def send(self, payload: Dict[str, Any]) -> None:
        """Send one request to the server."""
        if self.connection is None or self.closed:
            raise ConnectionError("Not connected to the chat server.")
        with self.send_lock:
            send_json(self.connection, payload)

    def _reader(self) -> None:
        """Read server events and put them on the GUI queue."""
        connection = self.connection
        try:
            while not self.closed and self.connection is connection and connection is not None:
                self.events.put(receive_json(connection))
        except (ConnectionError, OSError, ValueError):
            if not self.closed and self.connection is connection:
                self.events.put({"type": "network", "event": "disconnected", "message": "The server connection closed."})
        finally:
            if self.connection is connection:
                self.closed = True

    def close(self) -> None:
        """Close the socket and stop the reader thread."""
        self.closed = True
        if self.connection is not None:
            try:
                self.connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                self.connection.close()
            except OSError:
                pass
        self.connection = None


class ChatApp:
    """GUI with registration, login, room management, history, and alerts."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Advanced Multi-Room Chat")
        self.root.geometry("930x680")
        self.root.minsize(760, 560)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        self.events: "queue.Queue[Dict[str, Any]]" = queue.Queue()
        self.network = NetworkClient(self.events)
        self.connected = False
        self.username = ""
        self.current_room = ""
        self.window_focused = True

        self.host_var = tk.StringVar(value=HOST)
        self.port_var = tk.StringVar(value=str(PORT))
        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.room_var = tk.StringVar()
        self.new_room_var = tk.StringVar()
        self.message_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Connect to the server, then register or log in.")
        self.room_status_var = tk.StringVar(value="No room selected")

        self.login_frame: Optional[ttk.Frame] = None
        self.chat_frame: Optional[ttk.Frame] = None
        self.chat_text: Optional[tk.Text] = None
        self.room_combo: Optional[ttk.Combobox] = None
        self.message_entry: Optional[ttk.Entry] = None

        self._build_login_view()
        self.root.bind_all("<FocusIn>", lambda _event: self._set_focus(True))
        self.root.bind_all("<FocusOut>", lambda _event: self._set_focus(False))
        self.root.after(100, self._poll_events)

    def _set_focus(self, focused: bool) -> None:
        self.window_focused = focused

    def _build_login_view(self) -> None:
        """Build registration/login controls."""
        self.login_frame = ttk.Frame(self.root, padding=34)
        self.login_frame.pack(fill="both", expand=True)
        self.login_frame.columnconfigure(1, weight=1)

        ttk.Label(self.login_frame, text="Advanced Multi-Room Chat", font=("Arial", 22, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 6)
        )
        ttk.Label(
            self.login_frame,
            text="Socket networking • SQLite authentication • rooms • history • emoji shortcodes",
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 24))

        form = ttk.LabelFrame(self.login_frame, text="Server connection", padding=16)
        form.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 14))
        form.columnconfigure(1, weight=1)
        ttk.Label(form, text="Server host:").grid(row=0, column=0, sticky="w", pady=6)
        ttk.Entry(form, textvariable=self.host_var).grid(row=0, column=1, sticky="ew", pady=6)
        ttk.Label(form, text="Port:").grid(row=1, column=0, sticky="w", pady=6)
        ttk.Entry(form, textvariable=self.port_var, width=10).grid(row=1, column=1, sticky="w", pady=6)

        credentials = ttk.LabelFrame(self.login_frame, text="Account", padding=16)
        credentials.grid(row=3, column=0, columnspan=2, sticky="ew")
        credentials.columnconfigure(1, weight=1)
        ttk.Label(credentials, text="Username:").grid(row=0, column=0, sticky="w", pady=6)
        ttk.Entry(credentials, textvariable=self.username_var).grid(row=0, column=1, sticky="ew", pady=6)
        ttk.Label(credentials, text="Password:").grid(row=1, column=0, sticky="w", pady=6)
        ttk.Entry(credentials, textvariable=self.password_var, show="•").grid(
            row=1, column=1, sticky="ew", pady=6
        )
        button_row = ttk.Frame(credentials)
        button_row.grid(row=2, column=0, columnspan=2, sticky="e", pady=(12, 0))
        ttk.Button(button_row, text="Register", command=self.register).pack(side="left", padx=4)
        ttk.Button(button_row, text="Login", command=self.login).pack(side="left", padx=4)

        ttk.Label(self.login_frame, textvariable=self.status_var, foreground="#475569", wraplength=650).grid(
            row=4, column=0, columnspan=2, sticky="w", pady=(18, 0)
        )

    def _build_chat_view(self, rooms: List[str]) -> None:
        """Build the main chat view after successful login."""
        assert self.login_frame is not None
        self.login_frame.pack_forget()
        self.chat_frame = ttk.Frame(self.root, padding=14)
        self.chat_frame.pack(fill="both", expand=True)
        self.chat_frame.columnconfigure(1, weight=1)
        self.chat_frame.rowconfigure(1, weight=1)

        header = ttk.Frame(self.chat_frame)
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        header.columnconfigure(1, weight=1)
        ttk.Label(header, text="Chat", font=("Arial", 20, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(header, text="Signed in as "+self.username, foreground="#475569").grid(
            row=0, column=1, sticky="w", padx=16
        )
        ttk.Button(header, text="Logout", command=self.logout).grid(row=0, column=2, sticky="e")

        rooms_frame = ttk.LabelFrame(self.chat_frame, text="Rooms", padding=10)
        rooms_frame.grid(row=1, column=0, sticky="ns", padx=(0, 12))
        ttk.Label(rooms_frame, text="Join a room:").pack(anchor="w")
        self.room_combo = ttk.Combobox(rooms_frame, textvariable=self.room_var, values=rooms, state="readonly", width=23)
        self.room_combo.pack(fill="x", pady=(6, 5))
        ttk.Button(rooms_frame, text="Join Room", command=self.join_room).pack(fill="x", pady=3)
        ttk.Button(rooms_frame, text="Refresh Rooms", command=self.refresh_rooms).pack(fill="x", pady=3)
        ttk.Separator(rooms_frame).pack(fill="x", pady=12)
        ttk.Label(rooms_frame, text="Create a room:").pack(anchor="w")
        ttk.Entry(rooms_frame, textvariable=self.new_room_var, width=25).pack(fill="x", pady=(6, 5))
        ttk.Button(rooms_frame, text="Create Room", command=self.create_room).pack(fill="x", pady=3)
        ttk.Label(
            rooms_frame,
            text="Use :smile:, :heart:, :rocket:, :thumbsup:, or :tada:",
            wraplength=190,
            foreground="#475569",
        ).pack(anchor="w", pady=(20, 0))

        chat_panel = ttk.Frame(self.chat_frame)
        chat_panel.grid(row=1, column=1, sticky="nsew")
        chat_panel.columnconfigure(0, weight=1)
        chat_panel.rowconfigure(1, weight=1)
        ttk.Label(chat_panel, textvariable=self.room_status_var, font=("Arial", 12, "bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 6)
        )
        text_frame = ttk.Frame(chat_panel)
        text_frame.grid(row=1, column=0, sticky="nsew")
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)
        self.chat_text = tk.Text(text_frame, wrap="word", state="disabled", font=("Arial", 11), padx=10, pady=10)
        self.chat_text.grid(row=0, column=0, sticky="nsew")
        chat_scroll = ttk.Scrollbar(text_frame, orient="vertical", command=self.chat_text.yview)
        chat_scroll.grid(row=0, column=1, sticky="ns")
        self.chat_text.configure(yscrollcommand=chat_scroll.set)

        compose = ttk.Frame(chat_panel)
        compose.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        compose.columnconfigure(0, weight=1)
        self.message_entry = ttk.Entry(compose, textvariable=self.message_var)
        self.message_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.message_entry.bind("<Return>", lambda _event: self.send_message())
        ttk.Button(compose, text="Send", command=self.send_message).grid(row=0, column=1)

        ttk.Label(self.chat_frame, textvariable=self.status_var, foreground="#475569").grid(
            row=2, column=0, columnspan=2, sticky="w", pady=(12, 0)
        )

    def _ensure_connection(self) -> None:
        """Connect on demand using the host and port fields."""
        if self.connected and not self.network.closed:
            return
        try:
            host = self.host_var.get().strip()
            port = int(self.port_var.get().strip())
            if not host or not 1 <= port <= 65535:
                raise ValueError("Enter a valid host and port.")
            self.network.connect(host, port)
            self.connected = True
        except (ValueError, OSError, socket.timeout) as error:
            self.connected = False
            raise ConnectionError("Could not connect to the chat server: {}".format(error))

    def register(self) -> None:
        """Send a registration request to the SQLite-backed server."""
        try:
            self._ensure_connection()
            self.network.send(
                {"action": "register", "username": self.username_var.get(), "password": self.password_var.get()}
            )
            self.status_var.set("Registration request sent…")
        except (ConnectionError, OSError, ValueError) as error:
            self.status_var.set(str(error))

    def login(self) -> None:
        """Send a login request."""
        try:
            self._ensure_connection()
            self.network.send(
                {"action": "login", "username": self.username_var.get(), "password": self.password_var.get()}
            )
            self.status_var.set("Logging in…")
        except (ConnectionError, OSError, ValueError) as error:
            self.status_var.set(str(error))

    def refresh_rooms(self) -> None:
        """Ask the server for the current room list."""
        try:
            self.network.send({"action": "list_rooms"})
        except (ConnectionError, OSError, ValueError) as error:
            self.status_var.set(str(error))

    def create_room(self) -> None:
        """Create a room and offer to join it."""
        name = self.new_room_var.get().strip()
        if not name:
            self.status_var.set("Enter a room name first.")
            return
        try:
            self.network.send({"action": "create_room", "room": name})
        except (ConnectionError, OSError, ValueError) as error:
            self.status_var.set(str(error))

    def join_room(self) -> None:
        """Join the room selected in the combobox."""
        room = self.room_var.get().strip()
        if not room:
            self.status_var.set("Select a room first.")
            return
        try:
            self.network.send({"action": "join_room", "room": room})
            self.status_var.set("Joining {}…".format(room))
        except (ConnectionError, OSError, ValueError) as error:
            self.status_var.set(str(error))

    def send_message(self) -> None:
        """Send one message and clear the compose field."""
        body = self.message_var.get().strip()
        if not body:
            return
        try:
            self.network.send({"action": "send_message", "message": body})
            self.message_var.set("")
        except (ConnectionError, OSError, ValueError) as error:
            self.status_var.set(str(error))

    def logout(self) -> None:
        """Log out and return to the login view."""
        try:
            self.network.send({"action": "logout"})
        except (ConnectionError, OSError, ValueError):
            pass
        self._show_login("Logged out. You can log in again.")

    def _show_login(self, status: str) -> None:
        self.username = ""
        self.current_room = ""
        self.connected = False
        self.network.close()
        if self.chat_frame is not None:
            self.chat_frame.destroy()
            self.chat_frame = None
        if self.login_frame is not None:
            self.login_frame.pack(fill="both", expand=True)
        self.status_var.set(status)

    def _poll_events(self) -> None:
        """Dispatch network events on the Tkinter main thread."""
        try:
            while True:
                event = self.events.get_nowait()
                self._handle_event(event)
        except queue.Empty:
            pass
        self.root.after(100, self._poll_events)

    def _handle_event(self, event: Dict[str, Any]) -> None:
        """Update the GUI for a server response or incoming chat event."""
        if event.get("type") == "network":
            self._show_login(event.get("message", "Disconnected from server."))
            return
        if event.get("type") == "message":
            if event.get("room") == self.current_room:
                self._append_chat(
                    "[{}] {}: {}".format(
                        event.get("timestamp", "--:--"),
                        event.get("username", "Unknown"),
                        render_shortcodes(str(event.get("message", ""))),
                    )
                )
                if event.get("username") != self.username and not self.window_focused:
                    self.root.bell()
            return
        if event.get("type") == "system":
            if event.get("room") == self.current_room:
                self._append_chat("[{}] • {}".format(event.get("timestamp", "--:--"), event.get("message", "")))
                if not self.window_focused:
                    self.root.bell()
            return
        if event.get("type") != "response":
            return

        action = event.get("action")
        if not event.get("ok"):
            self.status_var.set(str(event.get("message", "The server rejected the request.")))
            return
        if action == "register":
            self.status_var.set(event.get("message", "Registration successful."))
        elif action == "login":
            self.username = str(event.get("username", self.username_var.get()))
            rooms = list(event.get("rooms", []))
            self._build_chat_view(rooms)
            self.status_var.set(event.get("message", "Logged in."))
            if "Lobby" in rooms:
                self.room_var.set("Lobby")
                self.join_room()
        elif action == "list_rooms":
            self._set_rooms(list(event.get("rooms", [])))
            self.status_var.set("Room list refreshed.")
        elif action == "create_room":
            rooms = list(event.get("rooms", []))
            self._set_rooms(rooms)
            new_room = str(event.get("room", ""))
            self.new_room_var.set("")
            self.room_var.set(new_room)
            self.status_var.set("Room created. Joining {}…".format(new_room))
            self.join_room()
        elif action == "join_room":
            self.current_room = str(event.get("room", ""))
            self.room_var.set(self.current_room)
            self.room_status_var.set("Room: {}".format(self.current_room))
            self._clear_chat()
            for message in event.get("history", []):
                self._append_chat(
                    "[{}] {}: {}".format(
                        message.get("timestamp", "--:--"),
                        message.get("username", "Unknown"),
                        render_shortcodes(str(message.get("message", ""))),
                    )
                )
            self.status_var.set(event.get("message", "Joined room."))
        elif action == "leave_room":
            self.current_room = ""
            self.room_status_var.set("No room selected")
            self._clear_chat()
            self.status_var.set(event.get("message", "Left room."))
        elif action == "logout":
            self._show_login(event.get("message", "Logged out."))

    def _set_rooms(self, rooms: List[str]) -> None:
        if self.room_combo is not None:
            self.room_combo["values"] = rooms

    def _clear_chat(self) -> None:
        if self.chat_text is not None:
            self.chat_text.configure(state="normal")
            self.chat_text.delete("1.0", tk.END)
            self.chat_text.configure(state="disabled")

    def _append_chat(self, line: str) -> None:
        if self.chat_text is None:
            return
        self.chat_text.configure(state="normal")
        self.chat_text.insert(tk.END, line + "\n")
        self.chat_text.see(tk.END)
        self.chat_text.configure(state="disabled")

    def close(self) -> None:
        """Close the socket and the GUI."""
        self.network.close()
        self.root.destroy()


def main() -> None:
    """Start the desktop chat client."""
    root = tk.Tk()
    ChatApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
