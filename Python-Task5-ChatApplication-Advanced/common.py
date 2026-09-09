"""Shared protocol, validation, password, and emoji helpers for chat."""

import hashlib
import hmac
import json
import re
import secrets
import socket
import struct
import time
from typing import Any, Dict, Optional

HOST = "127.0.0.1"
PORT = 5050
MAX_PACKET_SIZE = 1024 * 1024
USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,24}$")
ROOM_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _-]{0,31}$")

EMOJI_SHORTCODES = {
    ":smile:": "😄",
    ":grin:": "😁",
    ":joy:": "😂",
    ":heart:": "❤️",
    ":thumbsup:": "👍",
    ":+1:": "👍",
    ":thumbsdown:": "👎",
    ":wave:": "👋",
    ":fire:": "🔥",
    ":tada:": "🎉",
    ":rocket:": "🚀",
    ":thinking:": "🤔",
    ":sob:": "😭",
    ":laughing:": "😆",
    ":check:": "✅",
    ":warning:": "⚠️",
    ":star:": "⭐",
}


def send_json(connection: socket.socket, payload: Dict[str, Any]) -> None:
    """Send one length-prefixed JSON message over a TCP socket."""
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(encoded) > MAX_PACKET_SIZE:
        raise ValueError("Message is too large.")
    connection.sendall(struct.pack("!I", len(encoded)) + encoded)


def _receive_exact(connection: socket.socket, size: int) -> bytes:
    """Read exactly ``size`` bytes or raise ConnectionError on disconnect."""
    chunks = []
    remaining = size
    while remaining:
        chunk = connection.recv(remaining)
        if not chunk:
            raise ConnectionError("Peer disconnected.")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def receive_json(connection: socket.socket) -> Dict[str, Any]:
    """Receive one length-prefixed JSON object."""
    header = _receive_exact(connection, 4)
    (size,) = struct.unpack("!I", header)
    if size <= 0 or size > MAX_PACKET_SIZE:
        raise ValueError("Invalid packet size.")
    try:
        data = json.loads(_receive_exact(connection, size).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("Invalid JSON packet: {}".format(error))
    if not isinstance(data, dict):
        raise ValueError("Packet must contain a JSON object.")
    return data


def render_shortcodes(text: str) -> str:
    """Replace common chat shortcodes with Unicode emoji."""
    for shortcode, emoji in EMOJI_SHORTCODES.items():
        text = text.replace(shortcode, emoji)
    return text


def valid_username(username: str) -> bool:
    """Return whether a username is safe for display and storage."""
    return bool(USERNAME_RE.fullmatch(username.strip()))


def valid_room_name(room: str) -> bool:
    """Return whether a room name meets the server's naming policy."""
    return bool(ROOM_RE.fullmatch(room.strip()))


def hash_password(password: str, salt: Optional[bytes] = None) -> Dict[str, str]:
    """Hash a password with PBKDF2-HMAC-SHA256 and a random salt."""
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 180_000)
    return {"salt": salt.hex(), "digest": digest.hex()}


def verify_password(password: str, salt_hex: str, digest_hex: str) -> bool:
    """Compare a password hash in constant time."""
    try:
        expected = bytes.fromhex(digest_hex)
        salt = bytes.fromhex(salt_hex)
    except ValueError:
        return False
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 180_000)
    return hmac.compare_digest(actual, expected)


def timestamp() -> str:
    """Return a short local timestamp suitable for chat display."""
    return time.strftime("%H:%M")
