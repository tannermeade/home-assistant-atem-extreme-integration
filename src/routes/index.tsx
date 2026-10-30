import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";

export const Route = createFileRoute("/")({ component: Home });

const INPUTS = ["HDMI 1", "HDMI 2", "HDMI 3", "HDMI 4", "HDMI 5", "HDMI 6", "HDMI 7", "HDMI 8"];

const GROUPS: { title: string; rows: [string, string, string][] }[] = [
  {
    title: "Switching",
    rows: [
      ["Program", "select", "Control"],
      ["Preview", "select", "Control"],
      ["Take HDMI n", "button", "Control"],
      ["Cut / Auto", "button", "Control"],
      ["Transition style", "select", "Control"],
      ["Next transition layers", "switch", "Control"],
      ["Mix rate / FTB rate", "number", "Control"],
      ["Fade to black", "switch + button", "Control"],
      ["Transition position", "sensor", "Read-only"],
      ["Video mode", "sensor", "Read-only"],
    ],
  },
  {
    title: "Keyers and routing",
    rows: [
      ["Upstream key 1–4", "switch", "Control"],
      ["Downstream key on air", "switch", "Control"],
      ["Downstream key tie", "switch", "Control"],
      ["Downstream key auto", "button", "Control"],
      ["Aux output", "select", "Control"],
      ["Media player", "sensor", "Read-only"],
      ["Multiview", "sensor", "Read-only"],
      ["SuperSource boxes", "sensor", "Read-only"],
    ],
  },
  {
    title: "Fairlight audio",
    rows: [
      ["HDMI 1–8 level", "sensor", "Read-only"],
      ["HDMI / mic talking", "binary sensor", "Read-only"],
      ["Talking threshold", "number", "Config"],
      ["Mic 1 and Mic 2 level", "sensor", "Read-only"],
      ["Master level", "sensor", "Read-only"],
      ["Strip mix Off / On / AFV", "select", "Control"],
      ["Strip fader", "number", "Control"],
      ["Master fader", "number", "Control"],
      ["Master follows FTB", "switch", "Control"],
    ],
  },
  {
    title: "Record, stream, tally",
    rows: [
      ["Recording", "switch", "Control"],
      ["ISO record all inputs", "switch", "Control"],
      ["Recording status / duration / disk", "sensor", "Read-only"],
      ["Streaming", "switch", "Control"],
      ["Streaming status / bitrate", "sensor", "Read-only"],
      ["Program and preview tally", "binary sensor", "Read-only"],
    ],
  },
];

function Home() {
  const [program, setProgram] = useState(0);
  const [preview, setPreview] = useState(1);
  const [black, setBlack] = useState(false);
  const [style, setStyle] = useState("Mix");
  const [recording, setRecording] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [iso, setIso] = useState(true);
  const [usk, setUsk] = useState([false, false, false, false]);
  const [meters, setMeters] = useState<number[]>(() => INPUTS.map(() => -28));
  const [mics, setMics] = useState([-18, -22]);
  const [master, setMaster] = useState(-14);
  const [thresholds, setThresholds] = useState<number[]>(() => INPUTS.map(() => -40));
  const [micThresholds, setMicThresholds] = useState([-40, -40]);

  useEffect(() => {
    const id = window.setInterval(() => {
      const walk = (value: number, floor: number) => {
        const next = value + (Math.random() - 0.48) * 4;
        return Math.max(-60, Math.min(floor, next));
      };
      setMeters((prev) => prev.map((value, index) => walk(value, index === program && !black ? -6 : -36)));
      setMics((prev) => prev.map((value) => walk(value, -8)));
      setMaster((value) => (black ? Math.min(-40, value + 2) : walk(value, -8)));
    }, 500);
    return () => window.clearInterval(id);
  }, [program, black]);

  function take(index: number) {
    setPreview(program);
    setProgram(index);
    setBlack(false);
  }

  return (
    <main className="desk min-h-screen px-4 py-6 sm:px-8">
      <div className="mx-auto flex max-w-6xl flex-col gap-6">
        <header className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-xs tracking-[0.22em] text-[#9a958c] uppercase">Home Assistant · local push</p>
            <h1 className="mt-1 text-3xl font-semibold tracking-tight sm:text-4xl">ATEM Mini Extreme ISO</h1>
            <p className="mt-2 max-w-xl text-sm leading-relaxed text-[#b7b2a8]">
              Eight HDMI inputs, Fairlight meters, and the switcher buttons, as Home Assistant entities.
              This desk is a working model of those entities. Nothing here is talking to a switcher.
            </p>
          </div>
          <a
            href="/atem-extreme-ha.zip"
            className="panel inline-flex items-center justify-center px-4 py-2 text-sm font-medium text-[#eceae4]"
          >
            Download integration
          </a>
        </header>

        <section className="grid gap-4 lg:grid-cols-[minmax(0,1.3fr)_minmax(0,0.7fr)]">
          <div className="panel p-4">
            <div className="mb-3 flex items-center justify-between text-xs tracking-widest text-[#9a958c] uppercase">
              <span>Inputs</span>
              <span>Names come from the switcher</span>
            </div>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              {INPUTS.map((name, index) => {
                const onPgm = index === program;
                const onPvw = index === preview;
                return (
                  <button
                    key={name}
                    type="button"
                    onClick={() => take(index)}
                    className={`flex flex-col items-start gap-2 border px-3 py-3 text-left ${
                      onPgm ? "border-[#ff3b30] bg-[#2a1514]" : onPvw ? "border-[#3dd68c] bg-[#12241c]" : "border-[#2c3038] bg-[#14161b]"
                    }`}
                  >
                    <span className="flex w-full items-center justify-between text-[10px] tracking-widest uppercase">
                      <span className={onPgm ? "pgm" : onPvw ? "pvw" : "text-[#9a958c]"}>
                        {onPgm ? "Program" : onPvw ? "Preview" : "Idle"}
                      </span>
                      <span className={`h-2 w-2 rounded-full ${onPgm ? "bg-[#ff3b30]" : onPvw ? "bg-[#3dd68c]" : "bg-[#3a3e46]"}`} />
                    </span>
                    <span className="text-sm font-medium">{name}</span>
                  </button>
                );
              })}
            </div>

            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <Bus label="Program" tone="pgm" value={black ? "Black" : INPUTS[program]} />
              <Bus label="Preview" tone="pvw" value={INPUTS[preview]} />
            </div>

            <div className="mt-4 flex flex-wrap gap-2">
              <Action onClick={() => take(preview)}>Cut</Action>
              <Action onClick={() => take(preview)}>Auto</Action>
              <Action onClick={() => setBlack((value) => !value)} active={black}>
                {black ? "Fade from black" : "Fade to black"}
              </Action>
              {["Mix", "Dip", "Wipe", "DVE"].map((item) => (
                <button
                  key={item}
                  type="button"
                  onClick={() => setStyle(item)}
                  className={`border px-3 py-2 text-sm ${style === item ? "border-[#eceae4] text-[#eceae4]" : "border-[#2c3038] text-[#9a958c]"}`}
                >
                  {item}
                </button>
              ))}
            </div>

            <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
              {usk.map((on, index) => (
                <button
                  key={index}
                  type="button"
                  onClick={() => setUsk((prev) => prev.map((value, i) => (i === index ? !value : value)))}
                  className={`border px-3 py-2 text-left text-sm ${on ? "border-[#e2b657] text-[#e2b657]" : "border-[#2c3038] text-[#9a958c]"}`}
                >
                  USK {index + 1}
                  <span className="mt-1 block text-[10px] tracking-widest uppercase">{on ? "On air" : "Off"}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="panel flex flex-col gap-4 p-4">
            <div className="text-xs tracking-widest text-[#9a958c] uppercase">Fairlight · dB · 2 Hz</div>
            {INPUTS.map((name, index) => (
              <Meter key={name} label={name} db={meters[index]} hot={index === program && !black} />
            ))}
            <Meter label="Mic 1" db={mics[0]} hot={false} />
            <Meter label="Mic 2" db={mics[1]} hot={false} />
            <Meter label="Master" db={master} hot={!black} />
            <div className="mt-auto flex flex-wrap gap-2 pt-2">
              <Toggle on={recording} onClick={() => setRecording((v) => !v)} label="Record" />
              <Toggle on={streaming} onClick={() => setStreaming((v) => !v)} label="Stream" />
              <Toggle on={iso} onClick={() => setIso((v) => !v)} label="ISO" />
            </div>
          </div>
        </section>

        <section className="panel p-4">
          <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <h2 className="text-sm font-medium tracking-wide">Talking sensors</h2>
              <p className="mt-1 max-w-2xl text-sm leading-relaxed text-[#b7b2a8]">
                Each strip gets a boolean and a threshold. Talking turns on when that strip's level is at or above
                the number. These three are the close-ups and the wide shot. Mics get the same pair if the voices are on
                the XLRs instead of the HDMI audio.
              </p>
            </div>
            <p className="text-[10px] tracking-widest text-[#9a958c] uppercase">Default −40 dB · not sent to the switcher</p>
          </div>
          <div className="mt-4 grid gap-3 lg:grid-cols-3">
            {(
              [
                ["Camera 1 close-up", "HDMI 1 talking", meters[0], thresholds[0], 0],
                ["Camera 2 close-up", "HDMI 2 talking", meters[1], thresholds[1], 1],
                ["Wide · both people", "HDMI 3 talking", meters[2], thresholds[2], 2],
              ] as const
            ).map(([role, entity, db, threshold, index]) => (
              <TalkCard
                key={entity}
                role={role}
                entity={entity}
                db={db}
                threshold={threshold}
                onThreshold={(value) =>
                  setThresholds((prev) => prev.map((item, i) => (i === index ? value : item)))
                }
              />
            ))}
          </div>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            {mics.map((db, index) => (
              <TalkCard
                key={`mic-${index}`}
                role={`Mic ${index + 1}`}
                entity={`Mic ${index + 1} talking`}
                db={db}
                threshold={micThresholds[index]}
                onThreshold={(value) =>
                  setMicThresholds((prev) => prev.map((item, i) => (i === index ? value : item)))
                }
              />
            ))}
          </div>
        </section>

        <section className="grid gap-4 md:grid-cols-2">
          {GROUPS.map((group) => (
            <div key={group.title} className="panel p-4">
              <h2 className="text-sm font-medium tracking-wide">{group.title}</h2>
              <table className="mt-3 w-full text-left text-sm">
                <tbody>
                  {group.rows.map(([name, platform, access]) => (
                    <tr key={name} className="border-t border-[#2c3038]">
                      <td className="py-2 pr-3">{name}</td>
                      <td className="py-2 pr-3 text-[#9a958c]">{platform}</td>
                      <td className={`py-2 ${access === "Control" ? "text-[#e2b657]" : "text-[#7f8c9a]"}`}>{access}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}
        </section>

        <section className="panel p-4 text-sm leading-relaxed text-[#b7b2a8]">
          <h2 className="text-sm font-medium text-[#eceae4]">What is actually in the integration</h2>
          <p className="mt-2">
            A HACS custom component, <span className="text-[#eceae4]">atem_extreme</span>, speaks the ATEM UDP protocol
            directly. PyATEMMax was not used: the released library only has the classic audio mixer, and the Extreme ISO
            meters Fairlight levels on <span className="text-[#eceae4]">FMLv</span> and <span className="text-[#eceae4]">FDLv</span> after
            an <span className="text-[#eceae4]">SFLN</span> subscribe. Meters are throttled to 1–4 Hz. Each strip also gets a
            talking binary sensor and a talking-threshold number. The threshold stays in Home Assistant.
          </p>
          <p className="mt-2">
            No physical switcher was connected. Handshake, meter scaling, and the entity list are unit-tested against a
            fake switcher. SuperSource geometry, USB control, stream keys, EQ, and dynamics controls are not claimed.
            Dip, wipe, and DVE rates are read-only. The full list and the limitations are in the README inside the download.
          </p>
        </section>
      </div>
    </main>
  );
}

function Bus({ label, tone, value }: { label: string; tone: string; value: string }) {
  return (
    <div className="border border-[#2c3038] bg-[#14161b] px-3 py-3">
      <div className={`text-[10px] tracking-[0.2em] uppercase ${tone}`}>{label}</div>
      <div className="mt-1 text-2xl font-semibold">{value}</div>
    </div>
  );
}

function Action({ children, onClick, active }: { children: string; onClick: () => void; active?: boolean }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`border px-4 py-2 text-sm font-medium ${active ? "border-[#eceae4] bg-[#eceae4] text-[#101114]" : "border-[#3a3e46] bg-[#14161b]"}`}
    >
      {children}
    </button>
  );
}

function roundHalf(value: number) {
  return Math.max(-100, Math.min(6, Math.round(value * 2) / 2));
}

function TalkCard({
  role,
  entity,
  db,
  threshold,
  onThreshold,
}: {
  role: string;
  entity: string;
  db: number;
  threshold: number;
  onThreshold: (value: number) => void;
}) {
  const talking = db >= threshold;
  return (
    <div className={`border px-3 py-3 ${talking ? "border-[#ff4d43] bg-[#2a1514]" : "border-[#2c3038] bg-[#14161b]"}`}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-[10px] tracking-[0.18em] text-[#9a958c] uppercase">{role}</div>
          <div className="mt-1 text-sm font-medium">{entity}</div>
        </div>
        <span
          className={`border px-2 py-1 text-[10px] tracking-widest uppercase ${
            talking ? "border-[#ff4d43] text-[#ff4d43]" : "border-[#2c3038] text-[#9a958c]"
          }`}
        >
          {talking ? "On" : "Off"}
        </span>
      </div>
      <div className="mt-3 flex items-end justify-between gap-3 text-xs">
        <div className="flex flex-col gap-1 text-[#9a958c]">
          Threshold
          <div className="flex items-center gap-1">
            <button
              type="button"
              aria-label={`Lower ${entity} threshold`}
              onClick={() => onThreshold(roundHalf(threshold - 0.5))}
              className="border border-[#2c3038] bg-[#101114] px-2 py-1 text-sm text-[#eceae4]"
            >
              −
            </button>
            <span className="min-w-16 text-center text-sm tabular-nums text-[#eceae4]">{threshold.toFixed(1)}</span>
            <button
              type="button"
              aria-label={`Raise ${entity} threshold`}
              onClick={() => onThreshold(roundHalf(threshold + 0.5))}
              className="border border-[#2c3038] bg-[#101114] px-2 py-1 text-sm text-[#eceae4]"
            >
              +
            </button>
          </div>
        </div>
        <div className="text-right">
          <div className="text-[10px] tracking-widest text-[#9a958c] uppercase">Level</div>
          <div className="text-lg tabular-nums text-[#eceae4]">{db.toFixed(1)} dB</div>
        </div>
      </div>
    </div>
  );
}

function Meter({ label, db, hot }: { label: string; db: number; hot: boolean }) {
  const pct = Math.max(0, Math.min(100, ((db + 60) / 54) * 100));
  return (
    <div className="grid grid-cols-[4.5rem_1fr_3.2rem] items-center gap-2 text-xs">
      <span className="text-[#b7b2a8]">{label}</span>
      <span className="h-1.5 bg-[#101114]">
        <span className="block h-full" style={{ width: `${pct}%`, background: hot ? "#ff4d43" : "#d7d2c8" }} />
      </span>
      <span className="text-right tabular-nums text-[#eceae4]">{db.toFixed(1)}</span>
    </div>
  );
}

function Toggle({ on, label, onClick }: { on: boolean; label: string; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`border px-3 py-2 text-xs tracking-widest uppercase ${on ? "border-[#ff4d43] text-[#ff4d43]" : "border-[#2c3038] text-[#9a958c]"}`}
    >
      {label} {on ? "on" : "off"}
    </button>
  );
}
