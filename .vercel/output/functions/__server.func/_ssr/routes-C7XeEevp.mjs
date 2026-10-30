import { i as __toESM } from "../_runtime.mjs";
import { K as require_react, b as require_jsx_runtime } from "../_libs/@tanstack/react-router+[...].mjs";
//#region node_modules/.nitro/vite/services/ssr/assets/routes-C7XeEevp.js
var import_react = /* @__PURE__ */ __toESM(require_react());
var import_jsx_runtime = require_jsx_runtime();
var INPUTS = [
	"HDMI 1",
	"HDMI 2",
	"HDMI 3",
	"HDMI 4",
	"HDMI 5",
	"HDMI 6",
	"HDMI 7",
	"HDMI 8"
];
var GROUPS = [
	{
		title: "Switching",
		rows: [
			[
				"Program",
				"select",
				"Control"
			],
			[
				"Preview",
				"select",
				"Control"
			],
			[
				"Take HDMI n",
				"button",
				"Control"
			],
			[
				"Cut / Auto",
				"button",
				"Control"
			],
			[
				"Transition style",
				"select",
				"Control"
			],
			[
				"Next transition layers",
				"switch",
				"Control"
			],
			[
				"Mix rate / FTB rate",
				"number",
				"Control"
			],
			[
				"Fade to black",
				"switch + button",
				"Control"
			],
			[
				"Transition position",
				"sensor",
				"Read-only"
			],
			[
				"Video mode",
				"sensor",
				"Read-only"
			]
		]
	},
	{
		title: "Keyers and routing",
		rows: [
			[
				"Upstream key 1–4",
				"switch",
				"Control"
			],
			[
				"Downstream key on air",
				"switch",
				"Control"
			],
			[
				"Downstream key tie",
				"switch",
				"Control"
			],
			[
				"Downstream key auto",
				"button",
				"Control"
			],
			[
				"Aux output",
				"select",
				"Control"
			],
			[
				"Media player",
				"sensor",
				"Read-only"
			],
			[
				"Multiview",
				"sensor",
				"Read-only"
			],
			[
				"SuperSource boxes",
				"sensor",
				"Read-only"
			]
		]
	},
	{
		title: "Fairlight audio",
		rows: [
			[
				"HDMI 1–8 level",
				"sensor",
				"Read-only"
			],
			[
				"HDMI / mic talking",
				"binary sensor",
				"Read-only"
			],
			[
				"Talking threshold",
				"number",
				"Config"
			],
			[
				"Mic 1 and Mic 2 level",
				"sensor",
				"Read-only"
			],
			[
				"Master level",
				"sensor",
				"Read-only"
			],
			[
				"Strip mix Off / On / AFV",
				"select",
				"Control"
			],
			[
				"Strip fader",
				"number",
				"Control"
			],
			[
				"Master fader",
				"number",
				"Control"
			],
			[
				"Master follows FTB",
				"switch",
				"Control"
			]
		]
	},
	{
		title: "Record, stream, tally",
		rows: [
			[
				"Recording",
				"switch",
				"Control"
			],
			[
				"ISO record all inputs",
				"switch",
				"Control"
			],
			[
				"Recording status / duration / disk",
				"sensor",
				"Read-only"
			],
			[
				"Streaming",
				"switch",
				"Control"
			],
			[
				"Streaming status / bitrate",
				"sensor",
				"Read-only"
			],
			[
				"Program and preview tally",
				"binary sensor",
				"Read-only"
			]
		]
	}
];
function Home() {
	const [program, setProgram] = (0, import_react.useState)(0);
	const [preview, setPreview] = (0, import_react.useState)(1);
	const [black, setBlack] = (0, import_react.useState)(false);
	const [style, setStyle] = (0, import_react.useState)("Mix");
	const [recording, setRecording] = (0, import_react.useState)(false);
	const [streaming, setStreaming] = (0, import_react.useState)(false);
	const [iso, setIso] = (0, import_react.useState)(true);
	const [usk, setUsk] = (0, import_react.useState)([
		false,
		false,
		false,
		false
	]);
	const [meters, setMeters] = (0, import_react.useState)(() => INPUTS.map(() => -28));
	const [mics, setMics] = (0, import_react.useState)([-18, -22]);
	const [master, setMaster] = (0, import_react.useState)(-14);
	const [thresholds, setThresholds] = (0, import_react.useState)(() => INPUTS.map(() => -40));
	const [micThresholds, setMicThresholds] = (0, import_react.useState)([-40, -40]);
	(0, import_react.useEffect)(() => {
		const id = window.setInterval(() => {
			const walk = (value, floor) => {
				const next = value + (Math.random() - .48) * 4;
				return Math.max(-60, Math.min(floor, next));
			};
			setMeters((prev) => prev.map((value, index) => walk(value, index === program && !black ? -6 : -36)));
			setMics((prev) => prev.map((value) => walk(value, -8)));
			setMaster((value) => black ? Math.min(-40, value + 2) : walk(value, -8));
		}, 500);
		return () => window.clearInterval(id);
	}, [program, black]);
	function take(index) {
		setPreview(program);
		setProgram(index);
		setBlack(false);
	}
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("main", {
		className: "desk min-h-screen px-4 py-6 sm:px-8",
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "mx-auto flex max-w-6xl flex-col gap-6",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("header", {
					className: "flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "text-xs tracking-[0.22em] text-[#9a958c] uppercase",
							children: "Home Assistant · local push"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h1", {
							className: "mt-1 text-3xl font-semibold tracking-tight sm:text-4xl",
							children: "ATEM Mini Extreme ISO"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "mt-2 max-w-xl text-sm leading-relaxed text-[#b7b2a8]",
							children: "Eight HDMI inputs, Fairlight meters, and the switcher buttons, as Home Assistant entities. This desk is a working model of those entities. Nothing here is talking to a switcher."
						})
					] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("a", {
						href: "/atem-extreme-ha.zip",
						className: "panel inline-flex items-center justify-center px-4 py-2 text-sm font-medium text-[#eceae4]",
						children: "Download integration"
					})]
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", {
					className: "grid gap-4 lg:grid-cols-[minmax(0,1.3fr)_minmax(0,0.7fr)]",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "panel p-4",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "mb-3 flex items-center justify-between text-xs tracking-widest text-[#9a958c] uppercase",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: "Inputs" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: "Names come from the switcher" })]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
								className: "grid grid-cols-2 gap-2 sm:grid-cols-4",
								children: INPUTS.map((name, index) => {
									const onPgm = index === program;
									const onPvw = index === preview;
									return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
										type: "button",
										onClick: () => take(index),
										className: `flex flex-col items-start gap-2 border px-3 py-3 text-left ${onPgm ? "border-[#ff3b30] bg-[#2a1514]" : onPvw ? "border-[#3dd68c] bg-[#12241c]" : "border-[#2c3038] bg-[#14161b]"}`,
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
											className: "flex w-full items-center justify-between text-[10px] tracking-widest uppercase",
											children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
												className: onPgm ? "pgm" : onPvw ? "pvw" : "text-[#9a958c]",
												children: onPgm ? "Program" : onPvw ? "Preview" : "Idle"
											}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: `h-2 w-2 rounded-full ${onPgm ? "bg-[#ff3b30]" : onPvw ? "bg-[#3dd68c]" : "bg-[#3a3e46]"}` })]
										}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
											className: "text-sm font-medium",
											children: name
										})]
									}, name);
								})
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "mt-4 grid gap-3 sm:grid-cols-2",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Bus, {
									label: "Program",
									tone: "pgm",
									value: black ? "Black" : INPUTS[program]
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Bus, {
									label: "Preview",
									tone: "pvw",
									value: INPUTS[preview]
								})]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "mt-4 flex flex-wrap gap-2",
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Action, {
										onClick: () => take(preview),
										children: "Cut"
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Action, {
										onClick: () => take(preview),
										children: "Auto"
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Action, {
										onClick: () => setBlack((value) => !value),
										active: black,
										children: black ? "Fade from black" : "Fade to black"
									}),
									[
										"Mix",
										"Dip",
										"Wipe",
										"DVE"
									].map((item) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
										type: "button",
										onClick: () => setStyle(item),
										className: `border px-3 py-2 text-sm ${style === item ? "border-[#eceae4] text-[#eceae4]" : "border-[#2c3038] text-[#9a958c]"}`,
										children: item
									}, item))
								]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
								className: "mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4",
								children: usk.map((on, index) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
									type: "button",
									onClick: () => setUsk((prev) => prev.map((value, i) => i === index ? !value : value)),
									className: `border px-3 py-2 text-left text-sm ${on ? "border-[#e2b657] text-[#e2b657]" : "border-[#2c3038] text-[#9a958c]"}`,
									children: [
										"USK ",
										index + 1,
										/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
											className: "mt-1 block text-[10px] tracking-widest uppercase",
											children: on ? "On air" : "Off"
										})
									]
								}, index))
							})
						]
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "panel flex flex-col gap-4 p-4",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
								className: "text-xs tracking-widest text-[#9a958c] uppercase",
								children: "Fairlight · dB · 2 Hz"
							}),
							INPUTS.map((name, index) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Meter, {
								label: name,
								db: meters[index],
								hot: index === program && !black
							}, name)),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Meter, {
								label: "Mic 1",
								db: mics[0],
								hot: false
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Meter, {
								label: "Mic 2",
								db: mics[1],
								hot: false
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Meter, {
								label: "Master",
								db: master,
								hot: !black
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "mt-auto flex flex-wrap gap-2 pt-2",
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Toggle, {
										on: recording,
										onClick: () => setRecording((v) => !v),
										label: "Record"
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Toggle, {
										on: streaming,
										onClick: () => setStreaming((v) => !v),
										label: "Stream"
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Toggle, {
										on: iso,
										onClick: () => setIso((v) => !v),
										label: "ISO"
									})
								]
							})
						]
					})]
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", {
					className: "panel p-4",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
								className: "text-sm font-medium tracking-wide",
								children: "Talking sensors"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "mt-1 max-w-2xl text-sm leading-relaxed text-[#b7b2a8]",
								children: "Each strip gets a boolean and a threshold. Talking turns on when that strip's level is at or above the number. These three are the close-ups and the wide shot. Mics get the same pair if the voices are on the XLRs instead of the HDMI audio."
							})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "text-[10px] tracking-widest text-[#9a958c] uppercase",
								children: "Default −40 dB · not sent to the switcher"
							})]
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "mt-4 grid gap-3 lg:grid-cols-3",
							children: [
								[
									"Camera 1 close-up",
									"HDMI 1 talking",
									meters[0],
									thresholds[0],
									0
								],
								[
									"Camera 2 close-up",
									"HDMI 2 talking",
									meters[1],
									thresholds[1],
									1
								],
								[
									"Wide · both people",
									"HDMI 3 talking",
									meters[2],
									thresholds[2],
									2
								]
							].map(([role, entity, db, threshold, index]) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(TalkCard, {
								role,
								entity,
								db,
								threshold,
								onThreshold: (value) => setThresholds((prev) => prev.map((item, i) => i === index ? value : item))
							}, entity))
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "mt-3 grid gap-3 sm:grid-cols-2",
							children: mics.map((db, index) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(TalkCard, {
								role: `Mic ${index + 1}`,
								entity: `Mic ${index + 1} talking`,
								db,
								threshold: micThresholds[index],
								onThreshold: (value) => setMicThresholds((prev) => prev.map((item, i) => i === index ? value : item))
							}, `mic-${index}`))
						})
					]
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("section", {
					className: "grid gap-4 md:grid-cols-2",
					children: GROUPS.map((group) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "panel p-4",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
							className: "text-sm font-medium tracking-wide",
							children: group.title
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("table", {
							className: "mt-3 w-full text-left text-sm",
							children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("tbody", { children: group.rows.map(([name, platform, access]) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("tr", {
								className: "border-t border-[#2c3038]",
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("td", {
										className: "py-2 pr-3",
										children: name
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("td", {
										className: "py-2 pr-3 text-[#9a958c]",
										children: platform
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("td", {
										className: `py-2 ${access === "Control" ? "text-[#e2b657]" : "text-[#7f8c9a]"}`,
										children: access
									})
								]
							}, name)) })
						})]
					}, group.title))
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", {
					className: "panel p-4 text-sm leading-relaxed text-[#b7b2a8]",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
							className: "text-sm font-medium text-[#eceae4]",
							children: "What is actually in the integration"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
							className: "mt-2",
							children: [
								"A HACS custom component, ",
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "text-[#eceae4]",
									children: "atem_extreme"
								}),
								", speaks the ATEM UDP protocol directly. PyATEMMax was not used: the released library only has the classic audio mixer, and the Extreme ISO meters Fairlight levels on ",
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "text-[#eceae4]",
									children: "FMLv"
								}),
								" and ",
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "text-[#eceae4]",
									children: "FDLv"
								}),
								" after an ",
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "text-[#eceae4]",
									children: "SFLN"
								}),
								" subscribe. Meters are throttled to 1–4 Hz. Each strip also gets a talking binary sensor and a talking-threshold number. The threshold stays in Home Assistant."
							]
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "mt-2",
							children: "No physical switcher was connected. Handshake, meter scaling, and the entity list are unit-tested against a fake switcher. SuperSource geometry, USB control, stream keys, EQ, and dynamics controls are not claimed. Dip, wipe, and DVE rates are read-only. The full list and the limitations are in the README inside the download."
						})
					]
				})
			]
		})
	});
}
function Bus({ label, tone, value }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "border border-[#2c3038] bg-[#14161b] px-3 py-3",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: `text-[10px] tracking-[0.2em] uppercase ${tone}`,
			children: label
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "mt-1 text-2xl font-semibold",
			children: value
		})]
	});
}
function Action({ children, onClick, active }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
		type: "button",
		onClick,
		className: `border px-4 py-2 text-sm font-medium ${active ? "border-[#eceae4] bg-[#eceae4] text-[#101114]" : "border-[#3a3e46] bg-[#14161b]"}`,
		children
	});
}
function roundHalf(value) {
	return Math.max(-100, Math.min(6, Math.round(value * 2) / 2));
}
function TalkCard({ role, entity, db, threshold, onThreshold }) {
	const talking = db >= threshold;
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: `border px-3 py-3 ${talking ? "border-[#ff4d43] bg-[#2a1514]" : "border-[#2c3038] bg-[#14161b]"}`,
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "flex items-start justify-between gap-3",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "text-[10px] tracking-[0.18em] text-[#9a958c] uppercase",
				children: role
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "mt-1 text-sm font-medium",
				children: entity
			})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
				className: `border px-2 py-1 text-[10px] tracking-widest uppercase ${talking ? "border-[#ff4d43] text-[#ff4d43]" : "border-[#2c3038] text-[#9a958c]"}`,
				children: talking ? "On" : "Off"
			})]
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "mt-3 flex items-end justify-between gap-3 text-xs",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex flex-col gap-1 text-[#9a958c]",
				children: ["Threshold", /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-center gap-1",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
							type: "button",
							"aria-label": `Lower ${entity} threshold`,
							onClick: () => onThreshold(roundHalf(threshold - .5)),
							className: "border border-[#2c3038] bg-[#101114] px-2 py-1 text-sm text-[#eceae4]",
							children: "−"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
							className: "min-w-16 text-center text-sm tabular-nums text-[#eceae4]",
							children: threshold.toFixed(1)
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
							type: "button",
							"aria-label": `Raise ${entity} threshold`,
							onClick: () => onThreshold(roundHalf(threshold + .5)),
							className: "border border-[#2c3038] bg-[#101114] px-2 py-1 text-sm text-[#eceae4]",
							children: "+"
						})
					]
				})]
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "text-right",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "text-[10px] tracking-widest text-[#9a958c] uppercase",
					children: "Level"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "text-lg tabular-nums text-[#eceae4]",
					children: [db.toFixed(1), " dB"]
				})]
			})]
		})]
	});
}
function Meter({ label, db, hot }) {
	const pct = Math.max(0, Math.min(100, (db + 60) / 54 * 100));
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "grid grid-cols-[4.5rem_1fr_3.2rem] items-center gap-2 text-xs",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
				className: "text-[#b7b2a8]",
				children: label
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
				className: "h-1.5 bg-[#101114]",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
					className: "block h-full",
					style: {
						width: `${pct}%`,
						background: hot ? "#ff4d43" : "#d7d2c8"
					}
				})
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
				className: "text-right tabular-nums text-[#eceae4]",
				children: db.toFixed(1)
			})
		]
	});
}
function Toggle({ on, label, onClick }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
		type: "button",
		onClick,
		className: `border px-3 py-2 text-xs tracking-widest uppercase ${on ? "border-[#ff4d43] text-[#ff4d43]" : "border-[#2c3038] text-[#9a958c]"}`,
		children: [
			label,
			" ",
			on ? "on" : "off"
		]
	});
}
//#endregion
export { Home as component };
