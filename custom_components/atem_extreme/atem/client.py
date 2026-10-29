"""Asyncio ATEM client.

The switcher pushes state over UDP/9910. This client runs entirely on the
asyncio loop: handshake, ack, parse, and command send never block.
"""

from __future__ import annotations

import asyncio
import logging
import struct
import time
from typing import Callable

from ..const import (
    DEFAULT_ME,
    FAIRLIGHT_SOURCE_STEREO,
    MIX_AFV,
    MIX_OFF,
    MIX_ON,
)
from .audio import db_to_fairlight
from .protocol import (
    FLAG_ACK_REQUEST,
    FLAG_HELLO,
    FLAG_REQUEST_NEXT,
    HEADER_LEN,
    ack_packet,
    build_command,
    build_packet,
    hello_packet,
    parse_packet,
)
from .state import AtemState

_LOGGER = logging.getLogger(__name__)

Callback = Callable[["AtemClient"], None]

# Drop the session if the switcher goes silent. Desktop clients use ~1.5–5s.
RX_TIMEOUT = 5.0
INIT_TIMEOUT = 8.0


class AtemConnectionError(Exception):
    """The switcher could not be reached or the handshake failed."""


class SwitcherFullyBooked(AtemConnectionError):
    """The switcher refused the session because too many clients are connected."""


class AtemClient:
    """One UDP session with an ATEM switcher."""

    def __init__(
        self,
        host: str,
        port: int = 9910,
        *,
        on_state: Callback | None = None,
        on_connection: Callable[[bool], None] | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self.state = AtemState()
        self.on_state = on_state
        self.on_connection = on_connection
        self.connected = False
        self._ready = asyncio.Event()
        self._stop = asyncio.Event()
        self._task: asyncio.Task | None = None
        self._transport: asyncio.DatagramTransport | None = None
        self._session_id = 0
        self._local_id = 0
        self._last_rx = 0.0
        self._send_lock = asyncio.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._state_handle: asyncio.TimerHandle | None = None
        self._got_data = False
        self._fully_booked = False

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._loop = asyncio.get_running_loop()
        self._stop.clear()
        self._task = asyncio.create_task(self._run(), name=f"atem-{self.host}")

    async def stop(self) -> None:
        self._stop.set()
        self._close_transport()
        self._ready.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        self._set_connected(False)

    async def wait_until_ready(self, timeout: float = INIT_TIMEOUT) -> None:
        await asyncio.wait_for(self._ready.wait(), timeout)
        if self._fully_booked:
            raise SwitcherFullyBooked(f"{self.host} refused the connection (too many clients)")
        if not self.connected:
            raise AtemConnectionError(f"Not connected to {self.host}:{self.port}")

    def snapshot(self) -> AtemState:
        return self.state.copy()

    async def set_program(self, source: int, me: int = DEFAULT_ME) -> None:
        await self._send("CPgI", struct.pack(">BBH", me, 0, source))

    async def set_preview(self, source: int, me: int = DEFAULT_ME) -> None:
        await self._send("CPvI", struct.pack(">BBH", me, 0, source))

    async def cut(self, me: int = DEFAULT_ME) -> None:
        await self._send("DCut", struct.pack(">BBBB", me, 0, 0, 0))

    async def auto(self, me: int = DEFAULT_ME) -> None:
        await self._send("DAut", struct.pack(">BBBB", me, 0, 0, 0))

    async def fade_to_black(self, me: int = DEFAULT_ME) -> None:
        await self._send("FtbA", struct.pack(">BBBB", me, 0, 0, 0))

    async def set_transition_style(self, style: int, me: int = DEFAULT_ME) -> None:
        selection = self.state.transition_selection.get(me, 1)
        await self._send("CTTp", struct.pack(">BBBB", 0x01, me, style & 0xFF, selection & 0xFF))

    async def set_transition_selection(self, selection: int, me: int = DEFAULT_ME) -> None:
        style = self.state.transition_style.get(me, 0)
        await self._send("CTTp", struct.pack(">BBBB", 0x02, me, style & 0xFF, selection & 0xFF))

    async def set_mix_rate(self, frames: int, me: int = DEFAULT_ME) -> None:
        await self._send("CTMx", struct.pack(">BBBB", me, max(1, min(250, frames)), 0, 0))

    async def set_ftb_rate(self, frames: int, me: int = DEFAULT_ME) -> None:
        await self._send("FtbC", struct.pack(">BBBB", me, max(1, min(250, frames)), 0, 0))

    async def set_preview_transition(self, enabled: bool, me: int = DEFAULT_ME) -> None:
        await self._send("CTPr", struct.pack(">BBBB", me, 1 if enabled else 0, 0, 0))

    async def set_usk_on_air(self, keyer: int, enabled: bool, me: int = DEFAULT_ME) -> None:
        await self._send("CKOn", struct.pack(">BBBB", me, keyer, 1 if enabled else 0, 0))

    async def set_dsk_on_air(self, index: int, enabled: bool) -> None:
        await self._send("CDsL", struct.pack(">BBBB", index, 1 if enabled else 0, 0, 0))

    async def set_dsk_tie(self, index: int, enabled: bool) -> None:
        await self._send("CDsT", struct.pack(">BBBB", index, 1 if enabled else 0, 0, 0))

    async def dsk_auto(self, index: int) -> None:
        await self._send("DDsA", struct.pack(">BBBB", index, 0, 0, 0))

    async def set_aux(self, index: int, source: int) -> None:
        await self._send("CAuS", struct.pack(">BBH", 0x01, index, source))

    async def set_fairlight_mix(self, index: int, source: int, option: int) -> None:
        if option not in (MIX_OFF, MIX_ON, MIX_AFV):
            raise ValueError(f"Invalid Fairlight mix option {option}")
        await self._send("CFSP", _cfsp(index, source, mask=1 << 8, mix_option=option))

    async def set_fairlight_fader(self, index: int, source: int, db: float) -> None:
        raw = db_to_fairlight(db, minimum=-100.0, maximum=10.0)
        await self._send("CFSP", _cfsp(index, source, mask=1 << 7, fader=raw))

    async def set_master_fader(self, db: float) -> None:
        raw = db_to_fairlight(db, minimum=-100.0, maximum=10.0)
        buf = bytearray(20)
        buf[0] = 1 << 3  # faderGain mask
        struct.pack_into(">i", buf, 12, raw)
        await self._send("CFMP", bytes(buf))

    async def set_master_follow_ftb(self, enabled: bool) -> None:
        buf = bytearray(20)
        buf[0] = 1 << 4
        buf[16] = 1 if enabled else 0
        await self._send("CFMP", bytes(buf))

    async def set_recording(self, enabled: bool) -> None:
        await self._send("RcTM", struct.pack(">BBBB", 1 if enabled else 0, 0, 0, 0))

    async def set_streaming(self, enabled: bool) -> None:
        await self._send("StrR", struct.pack(">BBBB", 1 if enabled else 0, 0, 0, 0))

    async def set_record_all_inputs(self, enabled: bool) -> None:
        await self._send("ISOi", struct.pack(">BBBB", 1 if enabled else 0, 0, 0, 0))

    async def set_media_player_still(self, player: int, still: int) -> None:
        await self._send("MPSS", struct.pack(">BBBBBBBB", 0x01, player, 1, still & 0xFF, 0, 0, 0, 0))

    async def _run(self) -> None:
        backoff = 1.0
        while not self._stop.is_set():
            try:
                await self._session()
                backoff = 1.0
            except asyncio.CancelledError:
                raise
            except SwitcherFullyBooked:
                _LOGGER.warning("ATEM at %s is fully booked", self.host)
                self._fully_booked = True
                self._ready.set()
                self._set_connected(False)
                self._close_transport()
                break
            except Exception as err:  # noqa: BLE001 - reconnect on any session failure
                _LOGGER.warning("ATEM session %s:%s ended: %s", self.host, self.port, err)
            self._set_connected(False)
            self._close_transport()
            if self._stop.is_set():
                break
            try:
                await asyncio.wait_for(self._stop.wait(), backoff)
                break
            except asyncio.TimeoutError:
                pass
            backoff = min(backoff * 2, 20.0)

    async def _session(self) -> None:
        loop = asyncio.get_running_loop()
        self._session_id = 0
        self._local_id = 0
        self._got_data = False
        self._fully_booked = False
        self.state = AtemState()
        ready: asyncio.Future[None] = loop.create_future()

        def factory() -> _Protocol:
            return _Protocol(self, ready)

        transport, _protocol = await loop.create_datagram_endpoint(
            factory, remote_addr=(self.host, self.port)
        )
        self._transport = transport
        self._last_rx = time.monotonic()
        transport.sendto(hello_packet())
        try:
            await asyncio.wait_for(asyncio.shield(ready), INIT_TIMEOUT)
        except asyncio.TimeoutError as err:
            raise AtemConnectionError(f"Timed out waiting for {self.host} to finish initializing") from err
        if self._fully_booked:
            raise SwitcherFullyBooked(self.host)
        self._set_connected(True)
        self._ready.set()
        await self._enable_meters()
        self._schedule_state()
        while not self._stop.is_set():
            await asyncio.sleep(0.5)
            if time.monotonic() - self._last_rx > RX_TIMEOUT:
                raise AtemConnectionError("Switcher stopped sending")

    async def _enable_meters(self) -> None:
        if self.state.has_fairlight or not self.state.has_classic_audio:
            # Extreme ISO (and every Fairlight ATEM) meters only after SFLN.
            await self._send("SFLN", struct.pack(">BBBB", 1, 0, 0, 0))
        if self.state.has_classic_audio and not self.state.has_fairlight:
            await self._send("SALN", struct.pack(">BBBB", 1, 0, 0, 0))

    def _handle_datagram(self, data: bytes, ready: asyncio.Future[None]) -> None:
        packet = parse_packet(data)
        if packet is None:
            return
        self._last_rx = time.monotonic()
        if packet.session_id and not self._session_id:
            self._session_id = packet.session_id
        elif packet.session_id and packet.session_id != self._session_id:
            return

        if packet.flags & FLAG_HELLO:
            book = packet.raw[HEADER_LEN] if len(packet.raw) > HEADER_LEN else 0
            if book == 3:
                self._fully_booked = True
                if not ready.done():
                    ready.set_result(None)
                return
            self._send_raw(ack_packet(self._session_id, 0, hello_reply=True))
            return

        if packet.flags & FLAG_ACK_REQUEST:
            self._send_raw(ack_packet(self._session_id, packet.packet_id))

        if packet.flags & FLAG_REQUEST_NEXT:
            _LOGGER.debug("Switcher asked to resend packet %s; reconnecting if state stalls", packet.remote_packet_id)

        changed_state = False
        changed_levels = False
        for command in packet.commands:
            kind = self.state.apply(command)
            if kind == "levels":
                changed_levels = True
            elif kind:
                changed_state = True
            if command.name == "InCm":
                self.state.init_complete = True
        if packet.commands:
            self._got_data = True
        # Some firmware revisions never send InCm and instead go quiet with a
        # 12-byte keepalive once the initial dump is finished.
        if (
            not self.state.init_complete
            and self._got_data
            and packet.length == HEADER_LEN
            and packet.packet_id > 1
        ):
            self.state.init_complete = True
            changed_state = True
        if self.state.init_complete and not ready.done():
            ready.set_result(None)
        if self.connected and (changed_state or changed_levels):
            # Level packets arrive at 10 Hz. State listeners are debounced;
            # the integration publishes meters on its own timer.
            if changed_state:
                self._schedule_state()

    def _schedule_state(self) -> None:
        if self._state_handle is not None:
            return
        loop = self._loop
        if loop is None:
            return
        self._state_handle = loop.call_later(0.05, self._flush_state)

    def _flush_state(self) -> None:
        self._state_handle = None
        if self.on_state and self.connected:
            try:
                self.on_state(self)
            except Exception:  # noqa: BLE001
                _LOGGER.exception("ATEM state listener failed")

    def _set_connected(self, connected: bool) -> None:
        if self.connected == connected:
            return
        self.connected = connected
        if self.on_connection:
            try:
                self.on_connection(connected)
            except Exception:  # noqa: BLE001
                _LOGGER.exception("ATEM connection listener failed")

    async def _send(self, name: str, payload: bytes) -> None:
        if name not in {"SFLN", "SALN"} and not self.connected:
            raise AtemConnectionError("Switcher is not connected")
        async with self._send_lock:
            self._local_id = (self._local_id % 0x7FFF) + 1
            body = build_command(name, payload)
            packet = build_packet(
                FLAG_ACK_REQUEST,
                self._session_id,
                body,
                packet_id=self._local_id,
            )
            self._send_raw(packet)

    def _send_raw(self, packet: bytes) -> None:
        transport = self._transport
        if transport is None or transport.is_closing():
            return
        transport.sendto(packet)

    def _close_transport(self) -> None:
        transport = self._transport
        self._transport = None
        if transport is not None:
            transport.close()


class _Protocol(asyncio.DatagramProtocol):
    def __init__(self, client: AtemClient, ready: asyncio.Future[None]) -> None:
        self.client = client
        self.ready = ready

    def datagram_received(self, data: bytes, addr) -> None:  # noqa: ANN001
        self.client._handle_datagram(data, self.ready)

    def error_received(self, exc: Exception) -> None:
        _LOGGER.debug("ATEM socket error: %s", exc)

    def connection_lost(self, exc: Exception | None) -> None:
        if not self.ready.done():
            self.ready.set_exception(exc or AtemConnectionError("socket closed"))


def _cfsp(
    index: int,
    source: int,
    *,
    mask: int,
    mix_option: int = 0,
    fader: int = 0,
) -> bytes:
    buf = bytearray(48)
    struct.pack_into(">H", buf, 0, mask)
    struct.pack_into(">H", buf, 2, index)
    struct.pack_into(">q", buf, 8, source)
    struct.pack_into(">i", buf, 40, fader)
    buf[44] = mix_option & 0xFF
    return bytes(buf)


def stereo_source() -> int:
    return FAIRLIGHT_SOURCE_STEREO
