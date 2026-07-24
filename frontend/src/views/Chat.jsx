import { useRef, useState } from "react";
import { apiPost } from "../lib/api.js";
import RenderSpec from "../components/RenderSpec.jsx";
import EvidenceDrawer from "../components/EvidenceDrawer.jsx";

const SAMPLES = [
  "How many chain snatching cases in Bengaluru City in 2026?",
  "Show the monthly trend of chain snatching in Bengaluru City for 2026",
  "Are any of these cases connected?",
  "Show Prakash Rao's network",
  "Who are the top repeat offenders in Bengaluru City?",
  "ಈ ಸರಣಿಯ ಮುಂದಿನ ಗುರಿ ಎಲ್ಲಿ?",
];

export default function Chat({ role }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [lang, setLang] = useState("en");
  const [busy, setBusy] = useState(false);
  const listRef = useRef(null);

  async function send(text) {
    const q = (text ?? input).trim();
    if (!q || busy) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", text: q }]);
    setBusy(true);
    try {
      const resp = await apiPost("/api/chat", { session_id: "s-web", message: q, lang });
      setMessages((m) => [...m, { role: "assistant", resp }]);
      if (resp.answer_text) speak(resp.answer_text, lang);
    } catch (e) {
      setMessages((m) => [...m, { role: "assistant", resp: { error: e.message } }]);
    } finally {
      setBusy(false);
      setTimeout(() => listRef.current?.scrollTo(0, listRef.current.scrollHeight), 50);
    }
  }

  function listen() {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) return alert("Speech recognition not supported in this browser.");
    const rec = new SR();
    rec.lang = lang === "kn" ? "kn-IN" : "en-IN";
    rec.onresult = (e) => send(e.results[0][0].transcript);
    rec.start();
  }

  function speak(text, l) {
    if (!window.speechSynthesis) return;
    const u = new SpeechSynthesisUtterance(text);
    u.lang = l === "kn" ? "kn-IN" : "en-IN";
    window.speechSynthesis.speak(u);
  }

  return (
    <div className="mx-auto flex h-full max-w-3xl flex-col">
      <div className="mb-3 flex flex-wrap gap-2">
        {SAMPLES.map((s) => (
          <button key={s} onClick={() => send(s)}
            className="rounded-full border border-navy-700 px-3 py-1 text-xs text-slate-400 hover:bg-navy-800">
            {s}
          </button>
        ))}
      </div>

      <div ref={listRef} className="flex-1 space-y-4 overflow-y-auto">
        {messages.length === 0 && (
          <p className="text-slate-500">Ask about crimes, series, networks, offenders, or forecasts — in English or Kannada.</p>
        )}
        {messages.map((m, i) =>
          m.role === "user" ? (
            <div key={i} className="ml-auto max-w-[80%] rounded-lg bg-navy-700 px-3 py-2 font-kannada">{m.text}</div>
          ) : (
            <div key={i} className="max-w-[92%] rounded-lg bg-navy-900 px-3 py-2">
              {m.resp.error ? (
                <p className="text-red-400">{m.resp.error}{m.resp.suggestion && <span className="block text-slate-400">{m.resp.suggestion}</span>}</p>
              ) : (
                <>
                  <p className="whitespace-pre-wrap font-kannada">{m.resp.answer_text}</p>
                  <span className={`mt-1 inline-block text-[10px] uppercase ${m.resp.confidence === "high" ? "text-emerald-400" : m.resp.confidence === "low" ? "text-red-400" : "text-amber-400"}`}>
                    confidence: {m.resp.confidence}
                  </span>
                  {(m.resp.render_specs || []).map((s, j) => <RenderSpec key={j} spec={s} />)}
                  <EvidenceDrawer evidence={m.resp.evidence} />
                </>
              )}
            </div>
          )
        )}
        {busy && <div className="text-slate-500">Investigating…</div>}
      </div>

      <div className="mt-3 flex items-center gap-2">
        <select value={lang} onChange={(e) => setLang(e.target.value)}
          className="rounded-lg border border-navy-700 bg-navy-800 px-2 py-2 text-sm">
          <option value="en">EN</option>
          <option value="kn">ಕನ್</option>
        </select>
        <button onClick={listen} title="Speak" className="rounded-lg border border-navy-700 px-3 py-2 hover:bg-navy-800">🎤</button>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder="Ask ANVESHAK…"
          className="flex-1 rounded-lg border border-navy-700 bg-navy-800 px-3 py-2 outline-none focus:border-accent"
        />
        <button onClick={() => send()} disabled={busy}
          className="rounded-lg bg-accent px-4 py-2 font-medium text-white disabled:opacity-50">Send</button>
      </div>
    </div>
  );
}
