# ATEM Mini Extreme ISO for Home Assistant

Custom component for a Blackmagic **ATEM Mini Extreme ISO** (and the same protocol on other Fairlight ATEMs). The switcher is controlled over UDP port 9910. State is pushed; nothing is polled except a timer that publishes audio meters at 1–4 Hz so Home Assistant is not asked to store the switcher's 10 Hz meter stream.

**Not tested on hardware.** There was no switcher available while this was written. The handshake, Fairlight meter parsing, and command encoding are covered by unit tests against a fake switcher. Byte layouts follow the firmware 8+ map used by [sofie-atem-connection](https://github.com/Sofie-Automation/sofie-atem-connection) (MIT), which is what Bitfocus Companion talks to an Extreme ISO with. Treat the first connection to a real unit as a dress rehearsal.

## Why not PyATEMMax

[PyATEMMax](https://github.com/clvLabs/PyATEMMax) is a straight port of Skårhøj's ATEMmax and stops at the **classic** audio mixer (AMIP / AMLv). The Extreme ISO does not use that mixer. It uses Fairlight:

| What you need | PyATEMMax release | This integration |
| --- | --- | --- |
| Program / preview / cut / auto / FTB | Yes | Yes |
| Fairlight channel faders | No (open, unmerged PR #36, no meters) | Yes (`CFSP` / `FAMP`) |
| Fairlight level meters | No | Yes (`SFLN`, `FMLv`, `FDLv`) |
| asyncio, no thread in the HA loop | No, threaded sockets | Yes |

PyATEMMax is also GPL-3.0. This component is a small original client (Apache-2.0, see [LICENSE](LICENSE)) so it can sit in a Home Assistant config without pulling GPL into the integration.

Classic-mixer switchers still get best-effort level sensors if the switcher sends `AMIP`/`AMLv` and never sends Fairlight. That path is not the one the Extreme ISO uses.

## Install

Home Assistant 2024.11 or newer.

**HACS:** add this repository as a custom integration repository, install **ATEM Mini Extreme ISO**, restart.

**Manual:** copy `custom_components/atem_extreme` into `<config>/custom_components/` and restart.

Then **Settings → Devices & services → Add integration → ATEM Mini Extreme ISO**. Enter the switcher's IP. The default UDP port is `9910`. The integration opens a session, waits for the initial state dump, and only then creates entities from what the switcher actually reports (input names, keyer count, aux count, Fairlight strips).

Audio meter rate defaults to **2 Hz** (choices 1, 2, 3, 4). Change it under **Configure** on the integration. That only changes how often Home Assistant is notified. The switcher still sends meters at about 10 Hz; extra samples are dropped.

One config entry per host and port. Reconnects are automatic with backoff. If the switcher says it is full (too many software-control clients), setup fails with that error instead of looping.

## Entities

Names below are the entity name. Home Assistant prefixes them with the product name the switcher reports (`_pin`), for example `ATEM Mini Extreme ISO Program`. Counts follow the connected switcher. An Extreme ISO is 8 HDMI inputs, 2 mic inputs, 4 upstream keyers, 2 downstream keyers, Fairlight master.

Input names on program, preview, aux, and take buttons are the long names from the switcher (`InPr`), not hardcoded "HDMI 1".

### Switching

| Entity | Platform | Access | Notes |
| --- | --- | --- | --- |
| Program | select | control | Sets the program bus (`CPgI`). Options are every source the switcher says can go on M/E 1. |
| Preview | select | control | `CPvI`. |
| Take {input} | button | control | One per external input, plus Black and Color Bars. Hard-cuts that source to program. |
| Cut | button | control | `DCut`. Which layers move depends on Next transition. |
| Auto transition | button | control | `DAut`. |
| Transition style | select | control | Mix, Dip, Wipe, DVE, Stinger (`CTTp`). |
| Next transition background | switch | control | |
| Next transition key {n} | switch | control | One per upstream keyer. |
| Mix rate | number | control | Frames, 1–250 (`CTMx`). Dip, wipe, and DVE rates are read but not written. |
| Preview transition | switch | control | PREV TRANS (`CTPr`). |
| Transition position | sensor | read-only | Percent, diagnostic. |
| Transition in progress | binary sensor | read-only | |
| Video mode | sensor | read-only | Diagnostic. |
| Fade to black | switch | control | On when the output is fully black (`FtbS`). Turning it on or off runs `FtbA` only if the switcher is not already in that state. |
| Fade to black trigger | button | control | Always sends `FtbA`, same as the hardware button. |
| Fade to black rate | number | control | Frames (`FtbC`). |
| Fade to black running | binary sensor | read-only | |

### Keyers

| Entity | Platform | Access | Notes |
| --- | --- | --- | --- |
| Upstream key {n} | switch | control | On air (`CKOn` / `KeOn`). |
| Downstream key {n} | switch | control | On air (`CDsL` / `DskS`). |
| Downstream key {n} tie | switch | control | `CDsT`. |
| Downstream key {n} auto | button | control | `DDsA`. |
| Downstream key {n} transitioning | binary sensor | read-only | |

### Routing, multiview, SuperSource, media

| Entity | Platform | Access | Notes |
| --- | --- | --- | --- |
| Aux {n} | select | control | One per aux the switcher reports (`CAuS` / `AuxS`). |
| Media player {n} | sensor | read-only | Still or clip index from `MPCE`. Changing the still is not exposed; the command exists in the protocol but was not wired because a wrong still index is annoying and untested. |
| Multiview | sensor | read-only | Layout and window→source attributes (`MvPr`, `MvIn`). Only created when the switcher sends them. |
| SuperSource | sensor | read-only | Box enabled and source. Position and size are parsed with the single-SuperSource `SSBP` layout and **not verified on hardware**. Attribute `layout_verified_on_hardware` is false. |

### Audio (Fairlight)

Strips are discovered from `FAIP` + `FASP`. HDMI embedded audio uses the video input id. Original Extreme mic inputs are usually 1301 and 1302; Extreme ISO G2 XLR inputs are 1001 and 1002. The name comes from the id the switcher sends, so both revisions label themselves.

Meters are post-fader, the louder of left and right, in dB. The switcher's words are hundredths of a dB (`-1230` → `-12.3 dB`, `-10000` → `-100 dB` silence). Attributes: both channels, peaks, pre-dynamics input level, compressor / limiter / expander gain reduction. Fader entities are the gain you set, not the meter.

| Entity | Platform | Access | Notes |
| --- | --- | --- | --- |
| {strip} level | sensor | read-only | `FMLv`, sampled at the configured rate. |
| {strip} mix | select | control | Off, On, Audio follow video (`CFSP`). |
| {strip} fader | number | control | −100 dB to +10 dB (`CFSP`). Attributes include input gain, balance, EQ enable, delay. Those are not separate controls. |
| Master level | sensor | read-only | `FDLv`. |
| Master fader | number | control | `CFMP`. |
| Master follows fade to black | switch | control | `CFMP`. |

### Record and stream

Stream URL and stream key are deliberately not read. They are secrets and they are not needed to start or stop the encoder.

| Entity | Platform | Access | Notes |
| --- | --- | --- | --- |
| Recording | switch | control | `RcTM`. On only while status is recording. |
| Recording status | sensor | read-only | idle / recording / stopping, plus disk error attribute (`RTMS`). |
| Recording duration | sensor | read-only | Timecode (`RTMR`). |
| ISO record all inputs | switch | config | `ISOi`. This is the switcher's "record all inputs" setting, not a per-input ISO arm. |
| Recording disk {volume} | sensor | read-only | Seconds remaining and status (`RTMD`), one per mounted disk. |
| Streaming | switch | control | `StrR`. |
| Streaming status | sensor | read-only | idle / connecting / streaming / stopping (`StRS`). |
| Streaming bitrate | sensor | read-only | bit/s (`SRSS`). |
| Streaming duration | sensor | read-only | Timecode. |

### Tally

| Entity | Platform | Access | Notes |
| --- | --- | --- | --- |
| {input} program tally | binary sensor | read-only | `TlSr` bit 0. Diagnostic. |
| {input} preview tally | binary sensor | read-only | `TlSr` bit 1. Diagnostic. |

Created for external inputs (the 8 HDMI ports). Not created for Black, Color Bars, or media players.

## Services

There are no custom services. Automations should call the select, switch, number, and button entities. That keeps the device registry, the logbook, and the voice assistants on the same entities.

## Tests

```bash
python -m unittest tests.test_atem_extreme -v
```

The suite checks the hello packet, Fairlight `FMLv` scaling, recording/streaming bitfields, the entity catalog for an 8-input Extreme-shaped snapshot, and a full UDP handshake against a fake switcher (session, init dump, `SFLN`, meter ingest, `CPgI`).

`python -m compileall custom_components/atem_extreme` is the syntax check. Full `hassfest` needs a Home Assistant core checkout, which this environment does not have. The manifest matches the current custom-integration shape: config flow, `local_push`, no PyPI requirements, `translations/en.json` in sync with `strings.json`.

## Known limitations

- **No hardware test.** Expect to fix a field offset if a firmware build disagrees, especially SuperSource `SSBP`, preview-transition `CTPr`, and fade-to-black rate `FtbC`.
- Fairlight EQ bands, compressor, gate, limiter, and input-gain knobs are visible only as attributes, not controls.
- Dip, wipe, and DVE transition rates are not writable. Mix rate and fade-to-black rate are.
- Media-player still selection, macros, camera control, chroma-key parameters, HyperDecks, and multiview layout changes are read-only or absent.
- Dropped-packet retransmission is not implemented. The client acks, and if the switcher goes silent for 5 seconds it drops the session and handshakes again. On a clean LAN this is what you want; on a lossy link the initial dump can come up short until the next reconnect.
- Changing a Fairlight strip from stereo to dual-mono creates new source ids. New entities are added when the next state push arrives; removed strips stay as unavailable entities until you reload.
- Streaming credentials are not exposed on purpose.
- The integration speaks the Ethernet UDP protocol only, not the USB control channel on the Mini.

## Protocol notes

Session, in the usual order:

1. Client sends the 20-byte hello (`flags = 0x02`, marker `0x3A`).
2. Switcher answers with a session id. Book status `3` means fully booked.
3. Client acks the hello (marker `0x03`).
4. Switcher dumps state. Each reliable packet is acked.
5. `InCm`, or a 12-byte keepalive after real data, marks the session ready.
6. Client sends `SFLN` (Fairlight) or `SALN` (classic only) so meters start.

Commands the client writes: `CPgI`, `CPvI`, `DCut`, `DAut`, `FtbA`, `FtbC`, `CTTp`, `CTMx`, `CTPr`, `CKOn`, `CDsL`, `CDsT`, `DDsA`, `CAuS`, `CFSP`, `CFMP`, `RcTM`, `StrR`, `ISOi`, `SFLN`, `SALN`.
