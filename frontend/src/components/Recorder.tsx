import { useRef, useState } from "react";
import { useT } from "../i18n";

/** Tap to start, tap to stop. Returns the voice note as a Blob. */
export default function Recorder({ onRecorded }: { onRecorded: (audio: Blob | null) => void }) {
  const { t } = useT();
  const [state, setState] = useState<"idle" | "recording" | "done">("idle");
  const [error, setError] = useState("");
  const rec = useRef<MediaRecorder | null>(null);
  const chunks = useRef<Blob[]>([]);

  async function toggle() {
    if (state === "recording") {
      rec.current?.stop();
      return;
    }
    setError("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      // iPhone Safari records mp4; Chrome/Android record webm.
      const mimeType = MediaRecorder.isTypeSupported("audio/webm") ? "audio/webm" : "audio/mp4";
      const r = new MediaRecorder(stream, { mimeType });
      chunks.current = [];
      r.ondataavailable = (e) => e.data.size && chunks.current.push(e.data);
      r.onstop = () => {
        stream.getTracks().forEach((tr) => tr.stop());
        onRecorded(new Blob(chunks.current, { type: mimeType }));
        setState("done");
      };
      rec.current = r;
      r.start();
      setState("recording");
    } catch {
      setError("Microphone blocked. Allow it in your browser settings, or type the notes below.");
    }
  }

  return (
    <div className="flex flex-col items-center gap-3 py-4">
      <button
        type="button"
        onClick={toggle}
        aria-pressed={state === "recording"}
        className={`flex h-36 w-36 items-center justify-center rounded-full border-[6px] ${
          state === "recording" ? "border-flag bg-paper" : "border-paper bg-tape shadow-[0_3px_0_#B8930F]"
        }`}
      >
        {state === "recording" ? (
          <span className="h-10 w-10 rounded-[4px] bg-flag" />
        ) : (
          <svg width="52" height="52" viewBox="0 0 24 24" aria-hidden="true">
            <rect x="9" y="3" width="6" height="11" rx="3" fill="#1E2A36" />
            <path d="M6 11a6 6 0 0 0 12 0M12 17v4" stroke="#1E2A36" strokeWidth="2" fill="none" strokeLinecap="round" />
          </svg>
        )}
      </button>
      <p className="text-lg font-medium" aria-live="polite">
        {state === "idle" ? t.tapToRecord : state === "recording" ? t.recording : t.recorded}
      </p>
      {error && <p className="text-sm text-flag">{error}</p>}
    </div>
  );
}
