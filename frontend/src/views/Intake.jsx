import { useEffect, useRef, useState } from "react";
import { apiGet, apiPost } from "../lib/api.js";

// Prefilled with a witness-style chain-snatching account: the demo's live beat is
// filing a NEW FIR in ordinary words and watching it join the SH-07 series.
const SAMPLE_EN =
  "Yesterday evening around 7:30 pm my mother was walking by herself near the market " +
  "when two men riding a black motorbike came up from behind her. The man sitting at " +
  "the back grabbed her gold chain and they rode off fast the wrong way down the " +
  "one-way road. Both had their helmet visors pulled down.";

const SAMPLE_KN =
  "ನಿನ್ನೆ ಸಂಜೆ ಸುಮಾರು 7:30ಕ್ಕೆ ನನ್ನ ತಾಯಿ ಮಾರುಕಟ್ಟೆ ಬಳಿ ಒಬ್ಬರೇ ನಡೆದುಕೊಂಡು ಹೋಗುತ್ತಿದ್ದಾಗ " +
  "ಕಪ್ಪು ಬಣ್ಣದ ಬೈಕಿನಲ್ಲಿ ಬಂದ ಇಬ್ಬರು ಹಿಂಬದಿಯಿಂದ ಬಂದು ಚಿನ್ನದ ಸರವನ್ನು ಕಿತ್ತುಕೊಂಡು " +
  "ಒನ್-ವೇ ರಸ್ತೆಯಲ್ಲಿ ವಿರುದ್ಧ ದಿಕ್ಕಿನಲ್ಲಿ ಪರಾರಿಯಾದರು.";

export default function Intake() {
  const [masters, setMasters] = useState(null);
  const [narrative, setNarrative] = useState(SAMPLE_EN);
  const [district, setDistrict] = useState("Bengaluru City");
  const [station, setStation] = useState("Jayanagar PS");
  const [subHead, setSubHead] = useState("Chain Snatching");
  const [lang, setLang] = useState("en");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [err, setErr] = useState(null);
  const [listening, setListening] = useState(false);
  const recRef = useRef(null);

  useEffect(() => {
    apiGet("/api/masters").then(setMasters).catch(() => {});
  }, []);

  const stations = masters?.police_stations?.[district] || [];

  function listen() {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) return alert("Speech recognition is not supported in this browser.");
    if (listening) { recRef.current?.stop(); return; }
    const rec = new SR();
    rec.lang = lang === "kn" ? "kn-IN" : "en-IN";
    rec.continuous = true;
    rec.interimResults = true;
    let base = narrative ? narrative + " " : "";
    rec.onresult = (e) => {
      let text = "";
      for (let i = e.resultIndex; i < e.results.length; i++) text += e.results[i][0].transcript;
      setNarrative(base + text);
      if (e.results[e.results.length - 1].isFinal) base += text + " ";
    };
    rec.onend = () => setListening(false);
    rec.onerror = () => setListening(false);
    recRef.current = rec;
    setListening(true);
    rec.start();
  }

  async function submit() {
    setBusy(true); setErr(null); setResult(null);
    try {
      const body = { narrative, district, lang, crime_sub_head: subHead };
      if (station) body.police_station = station;
      setResult(await apiPost("/api/intake", body));
    } catch (e) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function reset() {
    setBusy(true); setErr(null);
    try {
      const r = await apiPost("/api/intake/reset");
      setResult(null);
      setErr(`Demo state restored — ${r.removed} case(s) removed, ${r.cases} in corpus.`);
    } catch (e) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold">File a new FIR</h2>
        <button onClick={reset} disabled={busy}
          className="rounded-lg border border-navy-700 px-3 py-1 text-xs text-slate-400 hover:bg-navy-800 disabled:opacity-50">
          Reset demo state
        </button>
      </div>
      <p className="mb-4 text-sm text-slate-400">
        Describe the incident in plain words — English or Kannada, typed or dictated.
        ANVESHAK embeds the narrative, re-runs linkage, and tells you instantly whether
        it belongs to a known serial-crime series.
      </p>

      <div className="space-y-3 rounded-lg border border-navy-700 bg-navy-900 p-4">
        <div className="flex flex-wrap gap-2">
          <select value={district} onChange={(e) => { setDistrict(e.target.value); setStation(""); }}
            className="rounded-lg border border-navy-700 bg-navy-800 px-2 py-1 text-sm">
            {(masters?.districts || [district]).map((d) => <option key={d}>{d}</option>)}
          </select>
          <select value={station} onChange={(e) => setStation(e.target.value)}
            className="rounded-lg border border-navy-700 bg-navy-800 px-2 py-1 text-sm">
            <option value="">(any station)</option>
            {stations.map((s) => <option key={s}>{s}</option>)}
          </select>
          <select value={subHead} onChange={(e) => setSubHead(e.target.value)}
            className="rounded-lg border border-navy-700 bg-navy-800 px-2 py-1 text-sm">
            {(masters?.crime_sub_heads || [subHead]).map((s) => <option key={s}>{s}</option>)}
          </select>
          <select value={lang}
            onChange={(e) => { const v = e.target.value; setLang(v); setNarrative(v === "kn" ? SAMPLE_KN : SAMPLE_EN); }}
            className="rounded-lg border border-navy-700 bg-navy-800 px-2 py-1 text-sm">
            <option value="en">EN</option>
            <option value="kn">ಕನ್</option>
          </select>
          <button onClick={listen} title="Dictate"
            className={`rounded-lg border px-3 py-1 text-sm ${listening ? "border-red-500 bg-red-950/40 text-red-300" : "border-navy-700 hover:bg-navy-800"}`}>
            {listening ? "● Listening…" : "🎤 Dictate"}
          </button>
        </div>

        <textarea value={narrative} onChange={(e) => setNarrative(e.target.value)} rows={6}
          placeholder="What happened?"
          className="w-full rounded-lg border border-navy-700 bg-navy-800 px-3 py-2 font-kannada text-sm outline-none focus:border-accent" />

        <div className="flex items-center gap-3">
          <button onClick={submit} disabled={busy || narrative.trim().length < 20}
            className="rounded-lg bg-accent px-4 py-2 font-medium text-white disabled:opacity-50">
            {busy ? "Registering & linking…" : "Register FIR"}
          </button>
          <span className="text-xs text-slate-500">
            Embeds the narrative and re-runs the linkage engine — usually a few seconds.
          </span>
        </div>
      </div>

      {err && <p className="mt-3 text-sm text-amber-400">{err}</p>}

      {result && (
        <div className="mt-4 rounded-lg border border-emerald-700 bg-emerald-950/30 p-4">
          <h3 className="font-semibold text-white">
            FIR registered · Case C-{result.case_id}
          </h3>
          <p className="mt-1 text-xs text-slate-400">
            {result.crime_sub_head} · {result.police_station}, {result.district} ·
            CrimeNo {result.crime_no} · narrative embedded at runtime
          </p>

          {result.series?.length > 0 ? (
            <div className="mt-3 border-t border-emerald-800 pt-3">
              <p className="text-sm text-emerald-300">
                🔗 This FIR matches an existing serial-crime series:
              </p>
              {result.series.map((s) => (
                <div key={s.series_id} className="mt-2">
                  <div className="text-lg font-semibold text-white">
                    {s.series_id} · {s.crime_sub_head}
                  </div>
                  <div className="text-sm text-slate-300">
                    now <b className="text-emerald-400">{s.case_count} linked cases</b> across{" "}
                    {s.districts.join(", ")} · confidence {(s.confidence * 100).toFixed(0)}%
                  </div>
                  <a href={`#/investigate?series=${s.series_id}`}
                    className="mt-2 inline-block rounded-lg bg-accent px-3 py-1 text-sm text-white">
                    Investigate {s.series_id} →
                  </a>
                </div>
              ))}
            </div>
          ) : (
            <p className="mt-3 border-t border-emerald-800 pt-3 text-sm text-slate-400">
              No existing series matched this modus operandi — the case is registered and
              will be reconsidered as new FIRs arrive.
            </p>
          )}
          <p className="mt-3 text-[11px] text-slate-500">
            Linkage re-scan completed in {(result.rescan_ms / 1000).toFixed(1)}s.
          </p>
        </div>
      )}
    </div>
  );
}
