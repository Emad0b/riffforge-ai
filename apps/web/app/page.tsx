"use client";
import { useEffect, useRef, useState } from "react";
import {
  AudioLines,
  ArrowUpRight,
  ChevronRight,
  Download,
  FileAudio,
  Guitar,
  Headphones,
  Layers3,
  LoaderCircle,
  Music2,
  Pause,
  Play,
  Plus,
  Repeat2,
  ShieldCheck,
  SlidersHorizontal,
  Trash2,
  Upload,
  WandSparkles,
  X,
} from "lucide-react";
type Note = {
  id: string;
  start: number;
  end: number;
  pitch: number;
  confidence: number;
  string: number;
  fret: number;
};
type Job = {
  id: string;
  name: string;
  duration: number;
  state: string;
  version: number;
  error?: string;
  result?: {
    notes: Note[];
    raw_notes: Note[];
    warnings: string[];
    model: string;
    seconds: number;
  };
};
const tuning = [40, 45, 50, 55, 59, 64];
const pitchName = (p: number) =>
  ["C", "C♯", "D", "D♯", "E", "F", "F♯", "G", "G♯", "A", "A♯", "B"][p % 12] +
  (Math.floor(p / 12) - 1);
export default function Studio() {
  const [token, setToken] = useState(""),
    [jobs, setJobs] = useState<Job[]>([]),
    [job, setJob] = useState<Job | null>(null),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [playing, setPlaying] = useState(false),
    [time, setTime] = useState(0),
    [loop, setLoop] = useState(false),
    [speed, setSpeed] = useState("1"),
    [selected, setSelected] = useState<Note | null>(null),
    [fret, setFret] = useState(0),
    [string, setString] = useState(1),
    [editBusy, setEditBusy] = useState(false);
  const waveform = useRef<HTMLDivElement>(null),
    wave = useRef<any>(null),
    file = useRef<HTMLInputElement>(null),
    loopRef = useRef(false);
  async function api(path: string, options: RequestInit = {}) {
    const r = await fetch("/api" + path, {
      ...options,
      headers: { Authorization: "Bearer " + token, ...options.headers },
    });
    if (!r.ok) {
      const e = await r.json().catch(() => ({ detail: "Request failed" }));
      throw Error(typeof e.detail === "string" ? e.detail : "Invalid input");
    }
    return r;
  }
  async function refresh() {
    const r = await api("/transcriptions");
    setJobs(await r.json());
  }
  useEffect(() => {
    let canceled = false;
    (async () => {
      let t = sessionStorage.getItem("riffforge-token");
      if (t) {
        const probe = await fetch("/api/transcriptions", {
          headers: { Authorization: "Bearer " + t },
        });
        if (!probe.ok) t = null;
      }
      if (!t) {
        const r = await fetch("/api/session", { method: "POST" });
        if (!r.ok) throw Error("API is unavailable. Start the backend.");
        t = (await r.json()).token;
        sessionStorage.setItem("riffforge-token", t!);
      }
      if (!canceled) setToken(t!);
    })().catch((e) => setError(e.message));
    return () => {
      canceled = true;
    };
  }, []);
  useEffect(() => {
    if (token) refresh().catch((e) => setError(e.message));
  }, [token]);
  useEffect(() => {
    if (!job || !["queued", "running"].includes(job.state)) return;
    const timer = setInterval(() => {
      api("/transcriptions/" + job.id)
        .then((r) => r.json())
        .then((j) => {
          setJob(j);
          if (j.state === "complete" || j.state === "failed") {
            setBusy(false);
            refresh();
          }
        })
        .catch((e) => {
          setError(e.message);
          setBusy(false);
        });
    }, 1000);
    return () => clearInterval(timer);
  }, [job?.id, job?.state, token]);
  useEffect(() => {
    let canceled = false,
      url = "";
    if (!job || job.state !== "complete" || !waveform.current) return;
    setTime(0);
    setPlaying(false);
    (async () => {
      const [{ default: WaveSurfer }, r] = await Promise.all([
        import("wavesurfer.js"),
        api("/transcriptions/" + job.id + "/audio"),
      ]);
      url = URL.createObjectURL(await r.blob());
      if (canceled) return;
      const w = WaveSurfer.create({
        container: waveform.current!,
        height: 95,
        waveColor: "#38394a",
        progressColor: "#c1fb70",
        cursorColor: "#eaf7d9",
        barWidth: 2,
        barGap: 3,
        url,
      });
      wave.current = w;
      w.on("timeupdate", (t: number) => setTime(t));
      w.on("play", () => setPlaying(true));
      w.on("pause", () => setPlaying(false));
      w.on("finish", () => {
        if (loopRef.current) {
          w.setTime(0);
          w.play();
        }
      });
      w.on("error", (e: Error) => setError(e.message));
    })().catch((e) => setError(e.message));
    return () => {
      canceled = true;
      wave.current?.destroy();
      wave.current = null;
      if (url) URL.revokeObjectURL(url);
    };
  }, [job?.id, job?.state]);
  useEffect(() => {
    loopRef.current = loop;
  }, [loop]);
  async function start(audio?: File) {
    setError("");
    setBusy(true);
    try {
      let r;
      if (audio) {
        const body = new FormData();
        body.append("file", audio);
        r = await api("/transcriptions", { method: "POST", body });
      } else r = await api("/demo", { method: "POST" });
      const j = await r.json();
      setJob(await (await api("/transcriptions/" + j.id)).json());
      await refresh();
    } catch (e: any) {
      setError(e.message);
      setBusy(false);
    }
  }
  async function open(j: Job) {
    try {
      setJob(await (await api("/transcriptions/" + j.id)).json());
      setSelected(null);
    } catch (e: any) {
      setError(e.message);
    }
  }
  async function download(format: string) {
    if (!job) return;
    try {
      const r = await api(`/transcriptions/${job.id}/export/${format}`);
      const url = URL.createObjectURL(await r.blob());
      const a = document.createElement("a");
      a.href = url;
      a.download = "riffforge." + format;
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (e: any) {
      setError(e.message);
    }
  }
  async function save() {
    if (!job?.result || !selected) return;
    setEditBusy(true);
    try {
      const notes = job.result.notes.map((n) =>
        n.id === selected.id
          ? { ...n, string, fret, pitch: tuning[6 - string] + fret }
          : n,
      );
      await api("/transcriptions/" + job.id, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ version: job.version, notes }),
      });
      setJob(await (await api("/transcriptions/" + job.id)).json());
      setSelected(null);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setEditBusy(false);
    }
  }
  const notes = job?.result?.notes || [],
    active = notes.find((n) => time >= n.start && time < n.end),
    complete = job?.state === "complete";
  return (
    <div className="shell">
      <aside>
        <a className="brand" href="/">
          <span className="brandmark">
            <AudioLines size={23} />
          </span>
          riff<span>forge</span>
          <small>AI</small>
        </a>
        <div className="workspace-label">YOUR WORKSPACE</div>
        <button className="nav active">
          <Guitar size={18} />
          Transcription studio
          <span className="navdot" />
        </button>
        <div className="library-head">
          RIFF LIBRARY <span>{jobs.length}</span>
        </div>
        <div className="library">
          {jobs.map((j) => (
            <div
              key={j.id}
              className={"riff " + (job?.id === j.id ? "current" : "")}
            >
              <button onClick={() => open(j)}>
                <FileAudio size={16} />
                <span>
                  {j.name}
                  <small>
                    {j.duration.toFixed(1)}s · {j.state}
                  </small>
                </span>
              </button>
              <button
                className="delete"
                aria-label={"Delete " + j.name}
                onClick={async () => {
                  try {
                    await api("/transcriptions/" + j.id, { method: "DELETE" });
                    if (job?.id === j.id) setJob(null);
                    refresh();
                  } catch (e: any) {
                    setError(e.message);
                  }
                }}
              >
                <Trash2 size={13} />
              </button>
            </div>
          ))}
          {!jobs.length && (
            <p className="library-empty">
              Your riffs will appear here.
              <br />
              Start with a short, clean recording.
            </p>
          )}
        </div>
        <div className="sidebar-bottom">
          <span className="online" />
          LOCAL WORKSPACE<small>Private audio · 24-hour session</small>
          <a
            href="https://github.com/Emad0b/riffforge-ai"
            target="_blank"
            rel="noreferrer"
          >
            View source <ArrowUpRight size={14} />
          </a>
        </div>
      </aside>
      <main>
        <header>
          <div className="breadcrumb">
            Workspace <ChevronRight size={14} />{" "}
            <span>Transcription studio</span>
          </div>
          <div className="header-right">
            <span className="phase">PHASE 01</span>
            <div className="avatar">EO</div>
          </div>
        </header>
        <section className="content">
          <div className="heading">
            <div>
              <span className="eyebrow">
                <span /> BUILT FOR THE RIFF
              </span>
              <h1>
                Hear it. <em>Forge it.</em>
              </h1>
              <p>Turn a guitar recording into a tab you can actually play.</p>
            </div>
            <div className="engine-badge">
              <span className="online" /> Basic Pitch{" "}
              <small>ONNX · CPU inference</small>
            </div>
          </div>
          {error && (
            <div role="alert" className="error">
              {error}
              <button aria-label="Dismiss error" onClick={() => setError("")}>
                <X size={16} />
              </button>
            </div>
          )}
          <div className="studio-grid">
            <div className="left-column">
              <section className="panel upload-panel">
                <div className="panel-head">
                  <span>
                    <Upload size={17} /> Start with your sound
                  </span>
                  <small>01 / INPUT</small>
                </div>
                <div
                  className="dropzone"
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={(e) => {
                    e.preventDefault();
                    if (!busy && e.dataTransfer.files[0])
                      start(e.dataTransfer.files[0]);
                  }}
                >
                  <div className="upload-symbol">
                    <AudioLines size={28} />
                  </div>
                  <h3>Drop your next riff here</h3>
                  <p>Clean guitar. One melody. Endless possibilities.</p>
                  <button
                    className="primary"
                    disabled={!token || busy}
                    onClick={() => file.current?.click()}
                  >
                    <Plus size={16} />
                    Choose audio file
                  </button>
                  <input
                    ref={file}
                    type="file"
                    aria-label="Upload audio"
                    accept="audio/*"
                    hidden
                    onChange={(e) => {
                      if (e.target.files?.[0]) start(e.target.files[0]);
                      e.target.value = "";
                    }}
                  />
                  <small>
                    WAV, MP3, FLAC, OGG, M4A · 1–30 seconds · 20 MB max
                  </small>
                </div>
                <div className="demo-row">
                  <div className="demo-icon">
                    <Music2 size={18} />
                  </div>
                  <div>
                    <strong>Just exploring?</strong>
                    <span>
                      Try our 15-second synthetic plucked-string riff.
                    </span>
                  </div>
                  <button
                    disabled={!token || busy}
                    onClick={() => start()}
                    aria-label="Transcribe reference riff"
                  >
                    Try a riff <ArrowUpRight size={16} />
                  </button>
                </div>
              </section>
              <section className="panel player-panel">
                <div className="panel-head">
                  <span>
                    <Headphones size={17} /> Listen & compare
                  </span>
                  <small>02 / AUDIO</small>
                </div>
                <div className="audio-title">
                  <div>
                    <h3>{job?.name || "Your sound starts here"}</h3>
                    <span>
                      {job
                        ? `${job.duration.toFixed(1)} seconds · Standard tuning`
                        : "Upload a riff to bring the waveform to life"}
                    </span>
                  </div>
                  <span className="filetag">MONO</span>
                </div>
                <div
                  ref={waveform}
                  className={"waveform " + (!complete ? "wave-empty" : "")}
                >
                  {!complete &&
                    Array.from({ length: 100 }, (_, i) => (
                      <i key={i} style={{ height: 12 + ((i * 17) % 48) }} />
                    ))}
                </div>
                <div className="transport">
                  <button
                    className="play"
                    aria-label={playing ? "Pause audio" : "Play audio"}
                    disabled={!complete}
                    onClick={() => wave.current?.playPause()}
                  >
                    {playing ? <Pause size={19} /> : <Play size={19} />}
                  </button>
                  <span className="time">
                    {time.toFixed(1)}{" "}
                    <small>/ {job?.duration.toFixed(1) || "0.0"}s</small>
                  </span>
                  <div className="transport-right">
                    <button
                      className={loop ? "toggled" : ""}
                      aria-label="Loop full clip"
                      aria-pressed={loop}
                      onClick={() => setLoop(!loop)}
                    >
                      <Repeat2 size={18} />
                    </button>
                    <select
                      aria-label="Playback speed"
                      value={speed}
                      onChange={(e) => {
                        setSpeed(e.target.value);
                        wave.current?.setPlaybackRate(
                          Number(e.target.value),
                          true,
                        );
                      }}
                    >
                      <option value="0.5">0.5×</option>
                      <option value="0.75">0.75×</option>
                      <option value="1">1.0×</option>
                      <option value="1.25">1.25×</option>
                    </select>
                  </div>
                </div>
              </section>
              <div className="pipeline">
                <span className="pipeline-title">UNDER THE HOOD</span>
                {[
                  "Decode & normalize",
                  "Detect MIDI notes",
                  "Optimize fingering",
                ].map((s, i) => (
                  <div key={s}>
                    <span>{i + 1}</span>
                    {s}
                    {i < 2 && <ChevronRight size={13} />}
                  </div>
                ))}
              </div>
            </div>
            <div className="right-column">
              <section className="panel tab-panel">
                <div className="panel-head">
                  <span>
                    <Guitar size={17} /> Your playable tab
                  </span>
                  <small>03 / OUTPUT</small>
                </div>
                <div className="tab-meta">
                  <span className="tuning">
                    <span /> E A D G B e
                  </span>
                  <span>STANDARD TUNING · 24 FRETS</span>
                </div>
                {!complete ? (
                  <div className="tab-empty">
                    <div className="empty-tab">
                      {["e", "B", "G", "D", "A", "E"].map((s) => (
                        <div key={s}>
                          <span>{s}</span>
                          <i />
                        </div>
                      ))}
                      <div className="tab-empty-overlay">
                        <span>
                          {busy ? (
                            <LoaderCircle className="spin" size={26} />
                          ) : (
                            <WandSparkles size={26} />
                          )}
                        </span>
                        <h3>
                          {busy
                            ? job?.state === "running"
                              ? "Finding the notes…"
                              : "Your riff is queued…"
                            : "A little sound. A playable idea."}
                        </h3>
                        <p>
                          {job?.state === "failed"
                            ? job.error
                            : busy
                              ? "Real model inference runs in a background worker."
                              : "Upload audio or try the reference riff to generate your tab."}
                        </p>
                      </div>
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="tab-scroll">
                      <svg
                        role="img"
                        aria-label="Interactive six-string guitar tablature"
                        width={Math.max(650, notes.length * 62 + 65)}
                        height="240"
                        viewBox={`0 0 ${Math.max(650, notes.length * 62 + 65)} 240`}
                      >
                        {["e", "B", "G", "D", "A", "E"].map((s, i) => (
                          <g key={s}>
                            <text
                              x="12"
                              y={45 + i * 29}
                              fill="#878997"
                              fontSize="13"
                            >
                              {s}
                            </text>
                            <line
                              x1="40"
                              y1={40 + i * 29}
                              x2={Math.max(650, notes.length * 62 + 65) - 15}
                              y2={40 + i * 29}
                              stroke="#3a3c49"
                            />
                          </g>
                        ))}
                        {notes.map((n, i) => (
                          <g
                            key={n.id}
                            onClick={() => {
                              setSelected(n);
                              setString(n.string);
                              setFret(n.fret);
                              wave.current?.setTime(n.start);
                            }}
                            className="tab-note"
                            role="button"
                            aria-label={`Edit ${pitchName(n.pitch)} string ${n.string} fret ${n.fret}`}
                            tabIndex={0}
                            onKeyDown={(e) => {
                              if (e.key === "Enter") {
                                setSelected(n);
                                setString(n.string);
                                setFret(n.fret);
                              }
                            }}
                          >
                            <rect
                              x={56 + i * 62}
                              y="20"
                              width="40"
                              height="180"
                              rx="7"
                              fill={
                                active?.id === n.id
                                  ? "#c1fb7015"
                                  : "transparent"
                              }
                            />
                            <rect
                              x={61 + i * 62}
                              y={30 + (n.string - 1) * 29}
                              width="30"
                              height="21"
                              rx="4"
                              fill={active?.id === n.id ? "#c1fb70" : "#20222d"}
                            />
                            <text
                              x={76 + i * 62}
                              y={45 + (n.string - 1) * 29}
                              textAnchor="middle"
                              fill={active?.id === n.id ? "#121510" : "#e3e5ed"}
                              fontSize="15"
                            >
                              {n.fret}
                            </text>
                            <text
                              x={76 + i * 62}
                              y="224"
                              textAnchor="middle"
                              fill="#666977"
                              fontSize="10"
                            >
                              {n.start.toFixed(1)}s
                            </text>
                          </g>
                        ))}
                      </svg>
                    </div>
                    <div className="tab-footer">
                      <span>
                        <SlidersHorizontal size={14} /> Click a note to refine
                        its fingering
                      </span>
                      <strong>{notes.length} notes</strong>
                    </div>
                  </>
                )}
                <div className="output-stats">
                  <div>
                    <span>DETECTED NOTES</span>
                    <strong>
                      {complete ? job.result!.raw_notes.length : "—"}
                    </strong>
                  </div>
                  <div>
                    <span>PLAYABLE NOTES</span>
                    <strong>{complete ? notes.length : "—"}</strong>
                  </div>
                  <div>
                    <span>INFERENCE TIME</span>
                    <strong>
                      {complete ? job.result!.seconds.toFixed(1) + "s" : "—"}
                    </strong>
                  </div>
                </div>
                <div className="exports">
                  <div>
                    <Download size={17} />
                    <span>
                      Take your riff with you
                      <small>Export the current, editable transcription</small>
                    </span>
                  </div>
                  <button disabled={!complete} onClick={() => download("mid")}>
                    MIDI <Download size={14} />
                  </button>
                  <button disabled={!complete} onClick={() => download("json")}>
                    JSON <Download size={14} />
                  </button>
                </div>
              </section>
              <div className="note-card">
                <ShieldCheck size={22} />
                <div>
                  <strong>Your ears have the final say.</strong>
                  <p>
                    This is a first-pass transcription, not a perfect score.
                    Check timing and pitches against your recording, then refine
                    the tab.
                  </p>
                  {job?.result?.warnings.map((w) => (
                    <small key={w}>{w}</small>
                  ))}
                </div>
              </div>
            </div>
          </div>
          <footer>
            <span>
              <Layers3 size={14} /> Clean audio → detected notes → playable tabs
            </span>
            <span>
              Built with Basic Pitch + dynamic programming{" "}
              <span className="footer-dot">•</span> v0.1
            </span>
          </footer>
        </section>
      </main>
      {selected && (
        <div className="modal-backdrop">
          <section
            className="edit-dialog"
            role="dialog"
            aria-modal="true"
            aria-label="Edit note"
          >
            <button
              className="close"
              aria-label="Close edit"
              onClick={() => setSelected(null)}
            >
              <X size={20} />
            </button>
            <span className="eyebrow">REFINE YOUR TAB</span>
            <h2>Edit {pitchName(selected.pitch)}</h2>
            <p>
              {selected.start.toFixed(2)}–{selected.end.toFixed(2)}s ·
              activation {selected.confidence.toFixed(2)}
            </p>
            <label>
              String
              <select
                value={string}
                onChange={(e) => setString(Number(e.target.value))}
              >
                {["e · high E", "B", "G", "D", "A", "E · low E"].map((s, i) => (
                  <option key={s} value={i + 1}>
                    {i + 1} · {s}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Fret
              <input
                type="number"
                min="0"
                max="24"
                value={fret}
                onChange={(e) => setFret(Number(e.target.value))}
              />
            </label>
            <p>
              Resulting pitch:{" "}
              <strong>{pitchName(tuning[6 - string] + fret)}</strong>
            </p>
            <button className="primary" disabled={editBusy} onClick={save}>
              Save correction
            </button>
            <small>
              Original model notes are preserved in your JSON export.
            </small>
          </section>
        </div>
      )}
    </div>
  );
}
