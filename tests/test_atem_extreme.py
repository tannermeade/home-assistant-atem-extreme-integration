"""Unit tests for the ATEM Extreme protocol, state, and entity catalog.

No switcher and no Home Assistant install are required. The handshake test
speaks UDP to an in-process fake switcher.
"""

from __future__ import annotations

import asyncio
import struct
import unittest

from custom_components.atem_extreme.atem.client import AtemClient
from custom_components.atem_extreme.atem.protocol import (
    FLAG_ACK,
    FLAG_ACK_REQUEST,
    FLAG_HELLO,
    build_command,
    build_packet,
    hello_packet,
    parse_packet,
)
from custom_components.atem_extreme.atem.state import AtemState, Levels
from custom_components.atem_extreme.catalog import build_specs
from custom_components.atem_extreme.const import FAIRLIGHT_SOURCE_STEREO
from custom_components.atem_extreme.talk import clamp_talk_threshold, is_talking
from custom_components.atem_extreme.values import async_write, read_value, strip_level


def _inpr(source: int, name: str, port: int = 0, me: int = 1) -> bytes:
    buf = bytearray(36)
    struct.pack_into(">H", buf, 0, source)
    encoded = name.encode()[:20]
    buf[2 : 2 + len(encoded)] = encoded
    buf[32] = port
    buf[35] = me
    return bytes(buf)


def _fasp(index: int, source: int, *, mix: int = 2, fader: int = -2000) -> bytes:
    buf = bytearray(52)
    struct.pack_into(">H", buf, 0, index)
    struct.pack_into(">q", buf, 8, source)
    struct.pack_into(">i", buf, 44, fader)
    buf[49] = mix
    return bytes(buf)


def _fmlv(index: int, source: int, left: int, right: int) -> bytes:
    buf = bytearray(42)
    struct.pack_into(">q", buf, 0, source)
    struct.pack_into(">H", buf, 8, index)
    struct.pack_into(">h", buf, 32, left)
    struct.pack_into(">h", buf, 34, right)
    struct.pack_into(">h", buf, 10, left - 50)
    return bytes(buf)


def _apply(state: AtemState, name: str, payload: bytes) -> str:
    from custom_components.atem_extreme.atem.protocol import AtemCommand

    return state.apply(AtemCommand(name, payload))


class ProtocolTests(unittest.TestCase):
    def test_hello_matches_the_well_known_packet(self) -> None:
        packet = hello_packet()
        self.assertEqual(len(packet), 20)
        self.assertEqual(packet[:2], bytes.fromhex("1014"))
        self.assertEqual(packet[9], 0x3A)
        self.assertEqual(packet[12], 0x01)
        parsed = parse_packet(packet)
        assert parsed is not None
        self.assertTrue(parsed.is_hello)
        self.assertEqual(parsed.length, 20)

    def test_command_roundtrip_preserves_payload(self) -> None:
        body = build_command("CPgI", struct.pack(">BBH", 0, 0, 4))
        packet = build_packet(FLAG_ACK_REQUEST, 0x10, body, packet_id=7)
        parsed = parse_packet(packet)
        assert parsed is not None
        self.assertEqual(parsed.packet_id, 7)
        self.assertTrue(parsed.needs_ack)
        self.assertEqual(parsed.commands[0].name, "CPgI")
        self.assertEqual(parsed.commands[0].payload[0], 0)
        self.assertEqual(int.from_bytes(parsed.commands[0].payload[2:4], "big"), 4)


class StateTests(unittest.TestCase):
    def test_fairlight_levels_are_hundredths_of_a_db(self) -> None:
        state = AtemState()
        _apply(state, "FAIP", struct.pack(">HBxxxxxxxxxxxxx", 1, 0))
        _apply(state, "FASP", _fasp(1, FAIRLIGHT_SOURCE_STEREO, mix=4, fader=-500))
        kind = _apply(state, "FMLv", _fmlv(1, FAIRLIGHT_SOURCE_STEREO, -1230, -1800))
        self.assertEqual(kind, "levels")
        levels = state.levels[(1, FAIRLIGHT_SOURCE_STEREO)]
        self.assertEqual(levels.left, -12.3)
        self.assertEqual(levels.right, -18.0)
        self.assertEqual(state.fairlight_sources[(1, FAIRLIGHT_SOURCE_STEREO)].mix_option, 4)
        self.assertEqual(state.fairlight_sources[(1, FAIRLIGHT_SOURCE_STEREO)].fader_gain, -500)

    def test_silence_floor(self) -> None:
        state = AtemState()
        _apply(state, "FMLv", _fmlv(2, FAIRLIGHT_SOURCE_STEREO, -10000, -10000))
        self.assertEqual(state.levels[(2, FAIRLIGHT_SOURCE_STEREO)].left, -100.0)

    def test_recording_and_streaming_bits(self) -> None:
        state = AtemState()
        _apply(state, "RTMS", struct.pack(">HxxI", 0x0001, 120))
        _apply(state, "StRS", struct.pack(">H", 0x0004))
        _apply(state, "ISOi", struct.pack(">B", 1))
        self.assertEqual(state.recording_status, "recording")
        self.assertEqual(state.recording_time_available, 120)
        self.assertEqual(state.streaming_status, "streaming")
        self.assertTrue(state.record_all_inputs)

    def test_program_preview_tally_and_keyers(self) -> None:
        state = AtemState()
        _apply(state, "InPr", _inpr(1, "Cam 1"))
        _apply(state, "InPr", _inpr(2, "Cam 2"))
        _apply(state, "PrgI", struct.pack(">BBH", 0, 0, 1))
        _apply(state, "PrvI", struct.pack(">BBH", 0, 0, 2))
        _apply(state, "_MeC", bytes([0, 4]))
        _apply(state, "KeOn", bytes([0, 0, 1, 0]))
        _apply(state, "DskS", bytes([0, 1, 0, 0, 1, 0]))
        _apply(state, "DskP", bytes([0, 1, 30]))
        tally = struct.pack(">HHBBHBB", 2, 1, 0x01, 0, 2, 0x02, 0)
        _apply(state, "TlSr", tally)
        self.assertEqual(state.program[0], 1)
        self.assertEqual(state.usk_ids(0), [0, 1, 2, 3])
        self.assertTrue(state.dsk[0].on_air)
        self.assertTrue(state.dsk[0].tie)
        self.assertEqual(state.dsk[0].rate, 30)
        self.assertEqual(state.tally[1], 0x01)
        self.assertEqual(state.tally[2], 0x02)


class CatalogTests(unittest.TestCase):
    def _extreme(self) -> AtemState:
        state = AtemState()
        state.product_name = "ATEM Mini Extreme ISO"
        state.has_fairlight = True
        _apply(state, "_MeC", bytes([0, 4]))
        for index in range(1, 9):
            _apply(state, "InPr", _inpr(index, f"HDMI {index}"))
            _apply(state, "FAIP", struct.pack(">HB", index, 0) + bytes(8))
            _apply(state, "FASP", _fasp(index, FAIRLIGHT_SOURCE_STEREO))
        for mic, name_type in ((1301, 2), (1302, 2)):
            _apply(state, "FAIP", struct.pack(">HB", mic, name_type) + bytes(8))
            _apply(state, "FASP", _fasp(mic, FAIRLIGHT_SOURCE_STEREO, mix=1))
        _apply(state, "InPr", _inpr(0, "Black", port=1))
        _apply(state, "InPr", _inpr(1000, "Color Bars", port=2))
        _apply(state, "PrgI", struct.pack(">BBH", 0, 0, 3))
        _apply(state, "PrvI", struct.pack(">BBH", 0, 0, 4))
        _apply(state, "FtbS", bytes([0, 0, 0, 0]))
        _apply(state, "FAMP", struct.pack(">BBxxiI?xxx", 6, 1, -1000, 0, 1)[:20])
        for keyer in range(4):
            _apply(state, "KeOn", bytes([0, keyer, 0, 0]))
        for dsk in range(2):
            _apply(state, "DskS", bytes([dsk, 0, 0, 0, 0, 0]))
            _apply(state, "DskP", bytes([dsk, 0, 25]))
        _apply(state, "AuxS", struct.pack(">BBH", 0, 0, 1))
        _apply(state, "RTMS", struct.pack(">HxxI", 0, 0))
        _apply(state, "StRS", struct.pack(">H", 1))
        _apply(state, "TrSS", bytes([0, 0, 0x01]))
        _apply(state, "TMxP", bytes([0, 30, 0, 0]))
        return state

    def test_extreme_iso_catalog_covers_the_requested_surface(self) -> None:
        state = self._extreme()
        specs = build_specs(state)
        by_key = {spec.key: spec for spec in specs}
        self.assertIn("me0_program", by_key)
        self.assertIn("me0_preview", by_key)
        self.assertFalse(by_key["me0_program"].read_only)
        self.assertFalse(by_key["me0_ftb"].read_only)
        self.assertFalse(by_key["me0_cut"].read_only)
        self.assertFalse(by_key["me0_auto"].read_only)
        for index in range(1, 9):
            self.assertIn(f"level_{index}_{FAIRLIGHT_SOURCE_STEREO}", by_key)
            self.assertTrue(by_key[f"level_{index}_{FAIRLIGHT_SOURCE_STEREO}"].read_only)
            self.assertFalse(by_key[f"mix_{index}_{FAIRLIGHT_SOURCE_STEREO}"].read_only)
            self.assertIn(f"take_{index}", by_key)
            self.assertIn(f"tally_pgm_{index}", by_key)
        self.assertIn(f"level_1301_{FAIRLIGHT_SOURCE_STEREO}", by_key)
        self.assertIn(f"level_1302_{FAIRLIGHT_SOURCE_STEREO}", by_key)
        self.assertIn("master_level", by_key)
        self.assertTrue(by_key["master_level"].read_only)
        self.assertFalse(by_key["master_fader"].read_only)
        self.assertFalse(by_key["recording"].read_only)
        self.assertFalse(by_key["streaming"].read_only)
        self.assertFalse(by_key["iso_recording"].read_only)
        self.assertIn("me0_usk_3", by_key)
        self.assertIn("dsk_1_on_air", by_key)
        self.assertIn("dsk_0_tie", by_key)
        self.assertIn("aux_0", by_key)
        self.assertEqual(read_value(state, by_key["me0_program"]), "HDMI 3")
        self.assertEqual(by_key["level_1_-65280"].unit, "dB")

    def test_mix_names_for_mics(self) -> None:
        state = self._extreme()
        specs = {spec.key: spec for spec in build_specs(state)}
        mic = specs[f"level_1301_{FAIRLIGHT_SOURCE_STEREO}"]
        self.assertIn("Mic 1", mic.name)

    def test_talking_follows_the_louder_channel_and_the_threshold(self) -> None:
        self.assertFalse(is_talking(None, -40))
        self.assertFalse(is_talking(-40.1, -40))
        self.assertTrue(is_talking(-40, -40))
        self.assertTrue(is_talking(-12.3, -40))
        self.assertEqual(clamp_talk_threshold(-12.24), -12.0)
        self.assertEqual(clamp_talk_threshold(50), 6.0)
        self.assertEqual(clamp_talk_threshold(-500), -100.0)

        state = self._extreme()
        specs = {spec.key: spec for spec in build_specs(state)}
        for index in range(1, 9):
            talk = specs[f"talking_{index}_{FAIRLIGHT_SOURCE_STEREO}"]
            threshold = specs[f"talk_threshold_{index}_{FAIRLIGHT_SOURCE_STEREO}"]
            self.assertEqual(talk.platform, "binary_sensor")
            self.assertTrue(talk.read_only)
            self.assertEqual(talk.name, f"HDMI {index} talking")
            self.assertEqual(threshold.platform, "number")
            self.assertFalse(threshold.read_only)
            self.assertEqual(threshold.unit, "dB")
            self.assertEqual(threshold.entity_category, "config")
            self.assertEqual(threshold.address, (index, FAIRLIGHT_SOURCE_STEREO))
        mic_talk = specs[f"talking_1301_{FAIRLIGHT_SOURCE_STEREO}"]
        self.assertEqual(mic_talk.name, "Mic 1 talking")
        self.assertNotIn("talking_master", specs)

        state.levels[(1, FAIRLIGHT_SOURCE_STEREO)] = Levels(left=-48.0, right=-22.5)
        level_spec = specs[f"talking_1_{FAIRLIGHT_SOURCE_STEREO}"]
        self.assertEqual(strip_level(state, level_spec), -22.5)
        self.assertTrue(is_talking(strip_level(state, level_spec), -30))
        self.assertFalse(is_talking(strip_level(state, level_spec), -20))


class SuperSourceTests(unittest.TestCase):
    def _roles(self) -> dict[str, int]:
        return {"screen": 4, "person1": 1, "person2": 2, "wide": 3}

    def _adjust(self, **kwargs):
        from custom_components.atem_extreme.supersource import SuperSourceAdjustments

        return SuperSourceAdjustments(**kwargs)

    def test_screen_left_tiles_the_frame(self) -> None:
        from custom_components.atem_extreme.supersource import build_preset, visible_edges

        built = build_preset("Screen left, cameras right", self._roles(), self._adjust())
        screen, top, bottom, spare = built.boxes
        self.assertEqual(built.background, 0)
        self.assertFalse(spare.enabled)
        self.assertEqual(screen.source, 4)
        self.assertEqual(top.source, 1)
        self.assertEqual(bottom.source, 2)
        self.assertFalse(screen.cropped)
        left, right, low, high = visible_edges(screen)
        cam_left, cam_right, cam_low, cam_high = visible_edges(top)
        bot_left, _bot_right, bot_low, bot_high = visible_edges(bottom)
        self.assertAlmostEqual(left, -16, delta=0.02)
        self.assertAlmostEqual(right, cam_left, delta=0.02)
        self.assertAlmostEqual(cam_right, 16, delta=0.02)
        self.assertAlmostEqual(high, cam_high, delta=0.02)
        self.assertAlmostEqual(cam_low, bot_high, delta=0.02)
        self.assertAlmostEqual(low, bot_low, delta=0.02)
        self.assertAlmostEqual(bot_left, cam_left, delta=0.02)
        self.assertLess(high, 9)
        self.assertGreater(top.y, 0)
        self.assertLess(bottom.y, 0)

    def test_zoom_crops_faces_and_keeps_the_screen_whole(self) -> None:
        from custom_components.atem_extreme.supersource import build_preset, visible_edges

        built = build_preset(
            "Screen left, cameras right, zoomed",
            self._roles(),
            self._adjust(zoom_column=0.25),
        )
        screen, top, bottom, _spare = built.boxes
        self.assertFalse(screen.cropped)
        self.assertAlmostEqual(screen.size, 0.75, places=2)
        self.assertGreater(top.crop_left, 0)
        self.assertAlmostEqual(top.crop_left, top.crop_right, places=3)
        self.assertEqual(top.crop_top, 0)
        _left, right, _low, high = visible_edges(screen)
        cam_left, cam_right, cam_low, cam_high = visible_edges(top)
        _b_left, _b_right, bot_low, bot_high = visible_edges(bottom)
        self.assertAlmostEqual(right, cam_left, delta=0.02)
        self.assertAlmostEqual(cam_right, 16, delta=0.02)
        self.assertAlmostEqual(high, cam_high, delta=0.02)
        self.assertAlmostEqual(cam_low, bot_high, delta=0.02)
        self.assertAlmostEqual(visible_edges(screen)[2], bot_low, delta=0.02)

    def test_sides_and_swap_only_move_the_named_sources(self) -> None:
        from custom_components.atem_extreme.supersource import build_preset

        roles = self._roles()
        plain = build_preset("Screen left, cameras right", roles, self._adjust())
        mirrored = build_preset("Screen right, cameras left", roles, self._adjust())
        swapped = build_preset("Screen left, cameras right, swapped", roles, self._adjust())
        self.assertLess(plain.boxes[0].x, 0)
        self.assertGreater(mirrored.boxes[0].x, 0)
        self.assertLess(mirrored.boxes[1].x, 0)
        self.assertEqual(swapped.boxes[1].source, 2)
        self.assertEqual(swapped.boxes[2].source, 1)
        self.assertEqual(plain.boxes[0].source, mirrored.boxes[0].source)

    def test_corner_sits_inside_the_chosen_corner(self) -> None:
        from custom_components.atem_extreme.supersource import build_preset, visible_edges

        built = build_preset(
            "Corner wide",
            self._roles(),
            self._adjust(corner="Bottom right", corner_size=0.30, corner_margin=0.8),
        )
        box = built.boxes[0]
        self.assertEqual(built.background, 4)
        self.assertEqual(box.source, 3)
        self.assertTrue(box.enabled)
        self.assertFalse(any(item.enabled for item in built.boxes[1:]))
        left, right, low, high = visible_edges(box)
        self.assertGreater(box.x, 0)
        self.assertLess(box.y, 0)
        self.assertAlmostEqual(right, 16 - 0.8, delta=0.02)
        self.assertAlmostEqual(low, -9 + 0.8, delta=0.02)
        self.assertLess(left, right)
        self.assertLess(low, high)
        top_left = build_preset(
            "Corner person 1",
            self._roles(),
            self._adjust(corner="Top left", corner_size=0.30, corner_margin=0.8),
        ).boxes[0]
        self.assertEqual(top_left.source, 1)
        self.assertLess(top_left.x, 0)
        self.assertGreater(top_left.y, 0)

    def test_nudge_waits_until_the_next_push(self) -> None:
        from custom_components.atem_extreme.supersource import build_preset

        small = build_preset("Corner person 2", self._roles(), self._adjust(corner_size=0.20))
        large = build_preset("Corner person 2", self._roles(), self._adjust(corner_size=0.40))
        self.assertEqual(small.boxes[0].source, 2)
        self.assertLess(small.boxes[0].size, large.boxes[0].size)

    def test_write_commands_use_the_firmware_8_layout(self) -> None:
        from custom_components.atem_extreme.supersource import build_preset, csbp_payload, cssc_payload

        built = build_preset("Screen left, cameras right", self._roles(), self._adjust())
        payload = csbp_payload(0, built.boxes[0])
        self.assertEqual(len(payload), 24)
        self.assertEqual(payload[0:2], bytes((0x03, 0xFF)))
        self.assertEqual(payload[2], 0)
        self.assertEqual(payload[3], 0)
        self.assertEqual(payload[4], 1)
        self.assertEqual(int.from_bytes(payload[6:8], "big"), 4)
        self.assertEqual(int.from_bytes(payload[8:10], "big", signed=True), -533)
        self.assertEqual(int.from_bytes(payload[10:12], "big", signed=True), 0)
        self.assertEqual(int.from_bytes(payload[12:14], "big"), 667)
        self.assertEqual(payload[14], 0)
        art = cssc_payload(built.background)
        self.assertEqual(art[0], 0x05)
        self.assertEqual(art[1], 0)
        self.assertEqual(int.from_bytes(art[2:4], "big"), 0)
        self.assertEqual(art[6], 0)
        corner = build_preset("Corner wide", self._roles(), self._adjust())
        self.assertEqual(int.from_bytes(cssc_payload(corner.background)[2:4], "big"), 4)

    def test_v8_state_matches_the_layout_that_would_be_pushed(self) -> None:
        from custom_components.atem_extreme.atem.protocol import AtemCommand
        from custom_components.atem_extreme.supersource import (
            SuperSourceAdjustments,
            build_preset,
            layout_matches,
            matching_preset,
        )

        adjustments = SuperSourceAdjustments()
        roles = self._roles()
        built = build_preset("Screen left, cameras right", roles, adjustments)
        state = AtemState()
        for index, box in enumerate(built.boxes):
            state.apply(AtemCommand("SSBP", _ssbp_echo(index, box)))
        state.apply(AtemCommand("SSrc", _ssrc_echo(built.background)))
        self.assertEqual(state.supersource_boxes[1]["source"], 1)
        self.assertAlmostEqual(state.supersource_boxes[0]["x"], built.boxes[0].x, delta=0.02)
        self.assertTrue(layout_matches(state, built))
        self.assertEqual(matching_preset(state, roles, adjustments), "Screen left, cameras right")
        self.assertFalse(layout_matches(state, build_preset("Corner wide", roles, adjustments)))

    def test_box_index_is_not_the_supersource_id(self) -> None:
        from custom_components.atem_extreme.atem.protocol import AtemCommand

        state = AtemState()
        payload = bytearray(24)
        payload[0] = 0
        payload[1] = 2
        payload[2] = 1
        struct.pack_into(">H", payload, 4, 7)
        state.apply(AtemCommand("SSBP", bytes(payload)))
        self.assertNotIn(0, state.supersource_boxes)
        self.assertEqual(state.supersource_boxes[2]["source"], 7)

    def test_catalog_exposes_every_preset_and_the_nudges(self) -> None:
        from custom_components.atem_extreme.supersource import preset_names

        specs = {spec.key: spec for spec in build_specs(self._extreme_state())}
        keys = [spec.key for spec in build_specs(self._extreme_state())]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertFalse(specs["ss_layout"].read_only)
        self.assertFalse(specs["ss_apply"].read_only)
        self.assertEqual(specs["ss_corner_size"].entity_category, "config")
        self.assertEqual(specs["ss_role_screen"].address, ("screen",))
        self.assertEqual(len(preset_names()), 12)
        self.assertIn("Corner wide", preset_names())
        self.assertIn("Screen left, cameras right, zoomed, swapped", preset_names())
        self.assertIn("Boxes off", preset_names())
        self.assertTrue(specs["supersource"].read_only)

    def _extreme_state(self) -> AtemState:
        state = AtemState()
        state.product_name = "ATEM Mini Extreme ISO"
        return state


def _ssbp_echo(index: int, box) -> bytes:
    from custom_components.atem_extreme.supersource import _wire

    buf = bytearray(24)
    buf[1] = index
    buf[2] = 1 if box.enabled else 0
    struct.pack_into(">H", buf, 4, box.source & 0xFFFF)
    struct.pack_into(">h", buf, 6, _wire(box.x, 100, signed=True))
    struct.pack_into(">h", buf, 8, _wire(box.y, 100, signed=True))
    struct.pack_into(">H", buf, 10, _wire(box.size, 1000, signed=False))
    buf[12] = 1 if box.cropped else 0
    struct.pack_into(">H", buf, 14, _wire(box.crop_top, 1000, signed=False))
    struct.pack_into(">H", buf, 16, _wire(box.crop_bottom, 1000, signed=False))
    struct.pack_into(">H", buf, 18, _wire(box.crop_left, 1000, signed=False))
    struct.pack_into(">H", buf, 20, _wire(box.crop_right, 1000, signed=False))
    return bytes(buf)


def _ssrc_echo(fill: int) -> bytes:
    buf = bytearray(16)
    struct.pack_into(">H", buf, 2, fill & 0xFFFF)
    return bytes(buf)


class HandshakeTests(unittest.IsolatedAsyncioTestCase):
    async def test_client_handshakes_enables_fairlight_meters_and_cuts(self) -> None:
        loop = asyncio.get_running_loop()
        switcher = _FakeSwitcher()
        transport, _protocol = await loop.create_datagram_endpoint(
            lambda: switcher, local_addr=("127.0.0.1", 0)
        )
        port = transport.get_extra_info("sockname")[1]
        client = AtemClient("127.0.0.1", port)
        try:
            await client.start()
            await client.wait_until_ready(3)
            self.assertTrue(client.connected)
            self.assertEqual(client.state.product_name, "ATEM Mini Extreme ISO")
            self.assertEqual(client.state.program[0], 1)
            self.assertTrue(client.state.has_fairlight)
            await asyncio.wait_for(switcher.seen_sfln.wait(), 2)
            self.assertEqual(switcher.sfln[0], 1)
            # Push a meter sample the way the switcher does after SFLN.
            switcher.send_meter()
            await asyncio.sleep(0.05)
            levels = client.state.levels[(1, FAIRLIGHT_SOURCE_STEREO)]
            self.assertEqual(levels.left, -12.0)
            self.assertIsNotNone(client.state.master_levels)
            await client.set_program(5)
            await asyncio.sleep(0.05)
            names = [command.name for command in switcher.commands]
            self.assertIn("CPgI", names)
            cpg = next(command for command in switcher.commands if command.name == "CPgI")
            self.assertEqual(int.from_bytes(cpg.payload[2:4], "big"), 5)
        finally:
            await client.stop()
            transport.close()


class _FakeSwitcher(asyncio.DatagramProtocol):
    def __init__(self) -> None:
        self.transport = None
        self.addr = None
        self.inited = False
        self.commands = []
        self.seen_sfln = asyncio.Event()
        self.sfln = b""
        self._packet_id = 1

    def connection_made(self, transport) -> None:  # noqa: ANN001
        self.transport = transport

    def datagram_received(self, data: bytes, addr) -> None:  # noqa: ANN001
        self.addr = addr
        packet = parse_packet(data)
        if packet is None:
            return
        if packet.is_hello:
            reply = build_packet(FLAG_HELLO, 0x0ABC, bytes([2, 0, 0, 1, 0, 0, 0, 0]))
            self.transport.sendto(reply, addr)
            return
        if not self.inited and (packet.flags & FLAG_ACK) and not packet.needs_ack:
            self.inited = True
            self._send_init(addr)
            return
        if packet.needs_ack:
            for command in packet.commands:
                self.commands.append(command)
                if command.name == "SFLN":
                    self.sfln = command.payload
                    self.seen_sfln.set()
            self.transport.sendto(build_packet(FLAG_ACK, 0x0ABC, remote_packet_id=packet.packet_id), addr)

    def _send(self, addr, commands: list[tuple[str, bytes]]) -> None:
        body = b"".join(build_command(name, payload) for name, payload in commands)
        packet = build_packet(FLAG_ACK_REQUEST, 0x0ABC, body, packet_id=self._packet_id)
        self._packet_id += 1
        self.transport.sendto(packet, addr)

    def _send_init(self, addr) -> None:
        commands: list[tuple[str, bytes]] = [
            ("_pin", b"ATEM Mini Extreme ISO\x00"),
            ("_ver", struct.pack(">HH", 2, 30)),
            ("_top", bytes([1, 16, 2, 1, 0, 2, 1, 0, 0, 1, 0, 1])),
            ("_MeC", bytes([0, 4, 0, 0])),
            ("InPr", _inpr(1, "HDMI 1")),
            ("InPr", _inpr(2, "HDMI 2")),
            ("PrgI", struct.pack(">BBH", 0, 0, 1)),
            ("PrvI", struct.pack(">BBH", 0, 0, 2)),
            ("FAIP", struct.pack(">HB", 1, 0) + bytes(8)),
            ("FASP", _fasp(1, FAIRLIGHT_SOURCE_STEREO)),
            ("FAIP", struct.pack(">HB", 1301, 2) + bytes(8)),
            ("FASP", _fasp(1301, FAIRLIGHT_SOURCE_STEREO, mix=1)),
            ("FAMP", bytes(20)),
            ("InCm", b""),
        ]
        self._send(addr, commands)

    def send_meter(self) -> None:
        assert self.addr is not None
        self._send(
            self.addr,
            [
                ("FMLv", _fmlv(1, FAIRLIGHT_SOURCE_STEREO, -1200, -1500)),
                ("FDLv", _master_meter()),
            ],
        )


def _master_meter() -> bytes:
    buf = bytearray(28)
    struct.pack_into(">h", buf, 20, -800)
    struct.pack_into(">h", buf, 22, -900)
    return bytes(buf)


class WriteTests(unittest.IsolatedAsyncioTestCase):
    async def test_ftb_only_sends_when_state_differs(self) -> None:
        sent = []

        class Stub:
            state = AtemState()

            async def fade_to_black(self, me: int = 0) -> None:
                sent.append(me)

            async def set_program(self, source: int, me: int = 0) -> None:
                sent.append(("program", source))

        stub = Stub()
        stub.state.ftb_black[0] = False
        from custom_components.atem_extreme.catalog import EntitySpec

        spec = EntitySpec("switch", "me0_ftb", "Fade to black", "ftb", (0,), False, "mdi:brightness-4")
        await async_write(stub, spec, True)  # type: ignore[arg-type]
        await async_write(stub, spec, False)  # type: ignore[arg-type]
        self.assertEqual(sent, [0])


if __name__ == "__main__":
    unittest.main()
