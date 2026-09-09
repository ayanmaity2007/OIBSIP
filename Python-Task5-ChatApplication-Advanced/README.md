# Advanced Multi-Room Chat Application

Advanced implementation of **Task 5 – Chat Application** for the Oasis Infobyte
Python Programming track.

This project uses a threaded TCP server and a Tkinter desktop client. The
server handles registration, PBKDF2 password authentication, multiple rooms,
SQLite message history, emoji shortcode rendering, and timestamped broadcasts.
The client provides a graphical login and chat experience.

## Features

### Beginner features included

- `server.py` listens for incoming client connections.
- `client.py` connects to the server on localhost or another host.
- Threaded, real-time, bidirectional messaging.
- Timestamped messages such as `[14:35] Alice: Hello`.
- Graceful disconnect notifications to other room members.
- Both scripts run on the same machine.

### Advanced features included

- Tkinter GUI client with login, rooms, history, and message composition.
- User registration and login. Passwords are salted and hashed with
  PBKDF2-HMAC-SHA256 before storage in SQLite.
- Named room creation and joining. A `Lobby` room is created automatically.
- The latest 100 messages are loaded when a user joins a room.
- Desktop/in-app notification using the window bell when a new message arrives
  while the window is unfocused.
- Common shortcodes such as `:smile:`, `:heart:`, `:rocket:`, `:thumbsup:`, and
  `:tada:` are rendered as Unicode emoji.
- Length-prefixed JSON protocol handles TCP packet boundaries correctly.
- Database and socket failures are converted into user-facing status messages.

## Run on One Machine

Open two or more terminals in this folder.

### 1. Start the server

```bash
python server.py
```

The server listens on `0.0.0.0:5050` and creates `chat.db`. For another port:

```bash
python server.py --host 0.0.0.0 --port 5051 --database chat-demo.db
```

### 2. Start one or more clients

In each additional terminal:

```bash
python client.py
```

Keep the default host `127.0.0.1` and port `5050` for same-machine testing.
Register different users, log in, join `Lobby`, and open multiple client windows
to exchange messages.

To connect across a trusted local network, run the server on its host address
and enter that address in the client. Do not expose this educational server to
the public internet without adding TLS, rate limiting, stronger account
controls, and operational security.

## Usage

1. Register a username containing 3–24 letters, numbers, or underscores.
2. Use a password of at least 8 characters.
3. Log in from the GUI.
4. Join `Lobby` or create a room using letters, numbers, spaces, `_`, and `-`.
5. Send messages with the Send button or Enter key.
6. Use emoji shortcodes such as `Great job :tada:`.
7. Leave the window unfocused to see and hear the in-app notification bell.

## Protocol and Storage Transparency

- The client and server exchange length-prefixed UTF-8 JSON over a TCP socket.
- User records in SQLite contain a username, random salt, PBKDF2 password
  digest, and creation timestamp. The plaintext password is never stored.
- Messages are stored in plaintext in `chat.db` with room, username, body, and
  timestamp so history can be loaded. The server renders supported shortcodes
  before storage.
- **Messages are not end-to-end encrypted.** Anyone with access to the server,
  database file, or unencrypted network traffic can potentially read them.
  This project does not provide TLS, forward secrecy, message signatures, or
  client-side encryption. The README intentionally documents this limitation.
- Passwords are not logged by the client or server. Protect `chat.db` and use
  a test environment.

## Project Structure

```text
Python-Task5-ChatApplication-Advanced/
├── common.py       # Framing, validation, hashing, and emoji helpers
├── server.py       # Threaded socket server and SQLite repository
├── client.py       # Tkinter GUI client
├── chat.db         # Created at runtime; do not commit private data
├── requirements.txt
└── README.md
```

## Troubleshooting

- If Tkinter is missing on Ubuntu/Debian, install `python3-tk`.
- If the client says the connection was refused, start `server.py` first and
  confirm host and port.
- If the port is in use, choose another port for the server and enter the same
  port in every client.
- If a GUI window is not available, run the server on a machine with Python and
  use the GUI client on a desktop machine that can reach it.
