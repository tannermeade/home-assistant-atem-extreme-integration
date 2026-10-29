"""ATEM UDP packet codec.

Packet layout matches the Skårhøj / PyATEMMax header (12 bytes) and the
8-byte command blocks used by every ATEM control client:

    uint16  flags(5 bits)<<11 | length(11 bits)
    uint16  session id
    uint16  acknowledged remote packet id
    uint16  reserved
    uint8   reserved
    uint8   hello/ack marker
    uint16  local packet id
    ...     command blocks

Command block:

    uint16  length (includes this 8-byte header)
    uint16  reserved
    char[4] name
    ...     payload
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field

HEADER_LEN = 12
CMD_HEADER_LEN = 8
UDP_PORT = 9910

FLAG_ACK_REQUEST = 0x01
FLAG_HELLO = 0x02
FLAG_RESEND = 0x04
FLAG_REQUEST_NEXT = 0x08
FLAG_ACK = 0x10


@dataclass
class AtemCommand:
    name: str
    payload: bytes


@dataclass
class AtemPacket:
    flags: int
    length: int
    session_id: int
    remote_packet_id: int
    marker: int
    packet_id: int
    commands: list[AtemCommand] = field(default_factory=list)
    raw: bytes = b""

    @property
    def is_hello(self) -> bool:
        return bool(self.flags & FLAG_HELLO)

    @property
    def needs_ack(self) -> bool:
        return bool(self.flags & FLAG_ACK_REQUEST)


def build_packet(
    flags: int,
    session_id: int,
    payload: bytes = b"",
    *,
    remote_packet_id: int = 0,
    packet_id: int = 0,
    marker: int = 0,
) -> bytes:
    length = HEADER_LEN + len(payload)
    if length > 0x07FF:
        raise ValueError(f"ATEM packet too large ({length})")
    buf = bytearray(length)
    word = ((flags & 0x1F) << 11) | (length & 0x07FF)
    struct.pack_into(">HHH", buf, 0, word, session_id & 0xFFFF, remote_packet_id & 0xFFFF)
    buf[9] = marker & 0xFF
    struct.pack_into(">H", buf, 10, packet_id & 0xFFFF)
    if payload:
        buf[HEADER_LEN:] = payload
    return bytes(buf)


def build_command(name: str, payload: bytes = b"") -> bytes:
    if len(name) != 4:
        raise ValueError(f"ATEM command name must be 4 bytes, got {name!r}")
    size = CMD_HEADER_LEN + len(payload)
    # The switcher expects command sizes padded to a multiple of 4.
    padded = size + ((4 - (size % 4)) % 4)
    buf = bytearray(padded)
    struct.pack_into(">H", buf, 0, padded)
    buf[4:8] = name.encode("ascii")
    if payload:
        buf[CMD_HEADER_LEN : CMD_HEADER_LEN + len(payload)] = payload
    return bytes(buf)


def hello_packet() -> bytes:
    """Initial handshake. Byte 9 = 0x3A and a 0x01 at offset 12, as every
    desktop client since the original SDK sends it."""
    return build_packet(FLAG_HELLO, 0, bytes(8), marker=0x3A)[:12] + bytes.fromhex(
        "0100000000000000"
    )


def ack_packet(session_id: int, remote_packet_id: int, *, hello_reply: bool = False) -> bytes:
    return build_packet(
        FLAG_ACK,
        session_id,
        remote_packet_id=remote_packet_id,
        marker=0x03 if hello_reply else 0x00,
    )


def parse_commands(body: bytes) -> list[AtemCommand]:
    commands: list[AtemCommand] = []
    index = 0
    while index + CMD_HEADER_LEN <= len(body):
        size = struct.unpack_from(">H", body, index)[0]
        if size < CMD_HEADER_LEN or index + size > len(body):
            break
        name = body[index + 4 : index + 8].decode("ascii", errors="replace")
        payload = bytes(body[index + CMD_HEADER_LEN : index + size])
        commands.append(AtemCommand(name, payload))
        index += size
    return commands


def parse_packet(data: bytes) -> AtemPacket | None:
    if len(data) < HEADER_LEN:
        return None
    word = struct.unpack_from(">H", data, 0)[0]
    flags = data[0] >> 3
    length = word & 0x07FF
    if length < HEADER_LEN or length > len(data):
        length = len(data)
    session_id, remote_packet_id = struct.unpack_from(">HH", data, 2)
    marker = data[9]
    packet_id = struct.unpack_from(">H", data, 10)[0]
    body = data[HEADER_LEN:length]
    commands = [] if flags & FLAG_HELLO else parse_commands(body)
    return AtemPacket(
        flags=flags,
        length=length,
        session_id=session_id,
        remote_packet_id=remote_packet_id,
        marker=marker,
        packet_id=packet_id,
        commands=commands,
        raw=data[:length],
    )


def cstring(payload: bytes, offset: int, length: int) -> str:
    chunk = payload[offset : offset + length]
    end = chunk.find(b"\x00")
    if end >= 0:
        chunk = chunk[:end]
    return chunk.decode("utf-8", errors="replace").strip()


def u8(payload: bytes, offset: int, default: int = 0) -> int:
    if offset >= len(payload):
        return default
    return payload[offset]


def u16(payload: bytes, offset: int, default: int = 0) -> int:
    if offset + 2 > len(payload):
        return default
    return struct.unpack_from(">H", payload, offset)[0]


def i16(payload: bytes, offset: int, default: int = 0) -> int:
    if offset + 2 > len(payload):
        return default
    return struct.unpack_from(">h", payload, offset)[0]


def u32(payload: bytes, offset: int, default: int = 0) -> int:
    if offset + 4 > len(payload):
        return default
    return struct.unpack_from(">I", payload, offset)[0]


def i32(payload: bytes, offset: int, default: int = 0) -> int:
    if offset + 4 > len(payload):
        return default
    return struct.unpack_from(">i", payload, offset)[0]


def i64(payload: bytes, offset: int, default: int = 0) -> int:
    if offset + 8 > len(payload):
        return default
    return struct.unpack_from(">q", payload, offset)[0]
