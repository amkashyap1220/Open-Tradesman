import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import Recorder from "../components/Recorder";
import { useT } from "../i18n";

const field = "w-full rounded-[4px] border border-rule bg-paper px-3 py-3 text-[17px]";

export default function NewJob() {
  const { t } = useT();
  const navigate = useNavigate();
  const [step, setStep] = useState<"customer" | "walkthrough">("customer");
  const [jobId, setJobId] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const [customer, setCustomer] = useState({
    customer_name: "",
    customer_email: "",
    customer_language: "en",
    address: "",
    billing_mode: "fixed",
  });
  const [audio, setAudio] = useState<Blob | null>(null);
  const [photos, setPhotos] = useState<File[]>([]);
  const [notes, setNotes] = useState("");

  async function createJob(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const job = await api.createJob(customer);
      setJobId(job.id);
      setStep("walkthrough");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function makeEstimate() {
    if (!jobId) return;
    setBusy(true);
    setError("");
    const form = new FormData();
    if (audio) form.append("audio", audio, audio.type.includes("mp4") ? "note.mp4" : "note.webm");
    photos.forEach((p) => form.append("photos", p));
    form.append("notes", notes);
    try {
      await api.walkthrough(jobId, form);
      navigate(`/jobs/${jobId}`);
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  }

  if (step === "customer") {
    return (
      <form onSubmit={createJob} className="space-y-4">
        <h1 className="font-cond text-3xl font-bold">{t.newJob}</h1>
        <label className="block space-y-1">
          <span className="text-slate-soft">{t.customerName}</span>
          <input required className={field} value={customer.customer_name}
            onChange={(e) => setCustomer({ ...customer, customer_name: e.target.value })} />
        </label>
        <label className="block space-y-1">
          <span className="text-slate-soft">{t.customerEmail}</span>
          <input required type="email" className={field} value={customer.customer_email}
            onChange={(e) => setCustomer({ ...customer, customer_email: e.target.value })} />
        </label>
        <label className="block space-y-1">
          <span className="text-slate-soft">{t.address}</span>
          <input className={field} value={customer.address}
            onChange={(e) => setCustomer({ ...customer, address: e.target.value })} />
        </label>
        <div className="grid grid-cols-2 gap-3">
          <label className="block space-y-1">
            <span className="text-slate-soft">{t.customerLanguage}</span>
            <select className={field} value={customer.customer_language}
              onChange={(e) => setCustomer({ ...customer, customer_language: e.target.value })}>
              <option value="en">English</option>
              <option value="es">Español</option>
              <option value="pl">Polski</option>
              <option value="pt">Português</option>
            </select>
          </label>
          <label className="block space-y-1">
            <span className="text-slate-soft">{t.billing}</span>
            <select className={field} value={customer.billing_mode}
              onChange={(e) => setCustomer({ ...customer, billing_mode: e.target.value })}>
              <option value="fixed">{t.fixed}</option>
              <option value="tm">{t.tm}</option>
            </select>
          </label>
        </div>
        {error && <p className="text-flag">{error}</p>}
        <button disabled={busy} className="h-14 w-full rounded-[4px] bg-slate-ink text-lg font-semibold text-paper disabled:opacity-50">
          {t.next}
        </button>
      </form>
    );
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="font-cond text-3xl font-bold">{t.walkthroughTitle}</h1>
        <p className="text-slate-soft">{t.walkthroughHint}</p>
      </div>

      <Recorder onRecorded={setAudio} />

      <label className="flex h-14 w-full cursor-pointer items-center justify-center rounded-[4px] border-2 border-dashed border-rule bg-paper text-[17px] font-medium">
        {t.addPhotos}{photos.length > 0 && ` (${photos.length})`}
        <input type="file" accept="image/*" capture="environment" multiple className="sr-only"
          onChange={(e) => setPhotos([...photos, ...Array.from(e.target.files ?? [])])} />
      </label>
      {photos.length > 0 && (
        <div className="flex gap-2 overflow-x-auto">
          {photos.map((p, i) => (
            <img key={i} src={URL.createObjectURL(p)} alt="" className="h-20 w-20 shrink-0 rounded-[4px] object-cover" />
          ))}
        </div>
      )}

      <label className="block space-y-1">
        <span className="text-slate-soft">{t.typedNotes}</span>
        <textarea rows={3} className={field} value={notes} onChange={(e) => setNotes(e.target.value)} />
      </label>

      {error && <p className="text-flag">{error}</p>}
      <button
        onClick={makeEstimate}
        disabled={busy || (!audio && !notes.trim())}
        className="h-14 w-full rounded-[4px] bg-slate-ink text-lg font-semibold text-paper disabled:opacity-50"
      >
        {busy ? t.working : t.makeEstimate}
      </button>
    </div>
  );
}
