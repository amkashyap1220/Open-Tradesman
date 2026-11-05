import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api, dollars, myTitle, type JobDetail as Detail, type LineItem } from "../api";
import { useT } from "../i18n";
import { jobNo } from "./JobRow";

function PriceInput({ item, onSaved }: { item: LineItem; onSaved: () => void }) {
  const { t } = useT();
  const [value, setValue] = useState("");
  return (
    <form
      className="mt-2 flex gap-2"
      onSubmit={async (e) => {
        e.preventDefault();
        const cents = Math.round(parseFloat(value) * 100);
        if (Number.isFinite(cents) && cents > 0) {
          await api.setPrice(item.id, cents);
          onSaved();
        }
      }}
    >
      <label className="flex flex-1 items-center gap-1 rounded-[4px] border border-flag px-2">
        <span className="text-sm text-flag">{t.setPrice}</span>
        <input inputMode="decimal" value={value} onChange={(e) => setValue(e.target.value)}
          className="figures w-full py-2 text-lg outline-none" aria-label={t.setPrice} />
      </label>
      <button className="rounded-[4px] bg-slate-ink px-4 font-semibold text-paper">OK</button>
    </form>
  );
}

export default function JobDetail() {
  const { t, lang } = useT();
  const id = Number(useParams().id);
  const [d, setD] = useState<Detail | null>(null);
  const [view, setView] = useState<"mine" | "customer">("mine");
  const [answers, setAnswers] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [updateError, setUpdateError] = useState("");
  const [notice, setNotice] = useState("");

  const load = () => api.job(id).then(setD).catch((e) => setError(e.message));
  useEffect(() => {
    load();
  }, [id]);

  /** Runs an action and reloads the job. Returns false (and sets the error) if it failed. */
  async function run(fn: () => Promise<unknown>, onError: (msg: string) => void = setError) {
    setBusy(true);
    setError("");
    setUpdateError("");
    try {
      await fn();
      await load();
      return true;
    } catch (e) {
      onError((e as Error).message);
      return false;
    } finally {
      setBusy(false);
    }
  }

  async function updateWithAnswers() {
    if (!d) return;
    const lines = d.questions.map((q, i) => (answers[i]?.trim() ? `${q[lang]} ${answers[i]}` : "")).filter(Boolean);
    const form = new FormData();
    form.append("notes", `${d.job.transcript}\n${lines.join("\n")}`);
    // Keep the answers if the update fails, so nothing typed is lost.
    if (await run(() => api.walkthrough(id, form), setUpdateError)) setAnswers([]);
  }

  if (!d) return <p className="p-4 text-slate-soft">{error || "…"}</p>;
  const text = (i: LineItem) => (view === "mine" ? (lang === "es" ? i.text_es : i.text_en) : i.text_customer);
  const canSend = d.totals.needs_price === 0 && d.line_items.length > 0 && d.job.status === "draft";

  return (
    <div className="space-y-5">
      <header>
        <p className="figures text-slate-soft">{t.workOrder} {jobNo(d.job.id)}</p>
        <h1 className="font-cond text-3xl font-bold leading-tight">{myTitle(d.job, lang) || d.customer.name}</h1>
        <p className="text-slate-soft">
          {d.customer.name} · {t.status[d.job.status] ?? d.job.status} · {d.job.billing_mode === "tm" ? t.tm : t.fixed}
        </p>
      </header>

      {d.questions.length > 0 && d.job.status === "draft" && (
        <section className="slip border-l-4 border-carbon p-4">
          <h2 className="mb-2 font-cond text-xl font-semibold">{t.questions}</h2>
          {d.totals.needs_price > 0 && <p className="mb-3 text-flag">{t.priceHint(d.totals.needs_price)}</p>}
          {d.questions.map((q, i) => (
            <label key={i} className="mb-3 block">
              <span className="text-[17px]">{q[lang]}</span>
              <input className="mt-1 w-full rounded-[4px] border border-rule px-3 py-2 disabled:bg-concrete" placeholder={t.answer}
                value={answers[i] ?? ""} disabled={busy}
                onChange={(e) => { const a = [...answers]; a[i] = e.target.value; setAnswers(a); }} />
            </label>
          ))}
          <button disabled={busy || !answers.some((a) => a?.trim())} onClick={updateWithAnswers}
            className="min-h-12 font-semibold text-carbon disabled:opacity-40" aria-busy={busy}>
            {busy ? t.updating : t.updateEstimate}
          </button>
          {updateError && <p className="mt-2 text-flag" role="alert">{updateError}</p>}
        </section>
      )}

      {/* Same estimate, two languages. */}
      <div role="tablist" className="grid grid-cols-2 rounded-[4px] bg-paper p-1">
        {(["mine", "customer"] as const).map((v) => (
          <button key={v} role="tab" aria-selected={view === v} onClick={() => setView(v)}
            className={`rounded-[3px] py-2 font-medium ${view === v ? "bg-slate-ink text-paper" : "text-slate-soft"}`}>
            {v === "mine" ? t.mine : t.asCustomer}
          </button>
        ))}
      </div>

      <section className="slip">
        {d.line_items.map((i) => (
          <div key={i.id} className={`slip-row px-4 py-3 ${i.needs_price ? "border-l-4 border-l-flag" : ""}`}>
            <div className="flex gap-3">
              <p className="flex-1 text-[17px]">{text(i)}</p>
              <p className="figures text-lg font-semibold">{i.needs_price ? "" : dollars(i.line_total_cents)}</p>
            </div>
            <p className="figures text-sm text-slate-soft">
              {i.quantity} {i.unit}{i.unit_price_cents != null && ` × ${dollars(i.unit_price_cents)}`}
              {i.low_confidence && <span className="ml-2 text-flag">{t.checkTranslation}</span>}
            </p>
            {i.needs_price && d.job.status === "draft" && <PriceInput item={i} onSaved={load} />}
          </div>
        ))}
        <div className="slip-row space-y-1 px-4 py-3">
          <div className="flex justify-between text-slate-soft"><span>{t.subtotal}</span><span className="figures">{dollars(d.totals.subtotal_cents)}</span></div>
          {d.totals.tax_cents > 0 && (
            <div className="flex justify-between text-slate-soft"><span>{t.tax}</span><span className="figures">{dollars(d.totals.tax_cents)}</span></div>
          )}
          <div className="flex items-baseline justify-between">
            <span className="text-lg font-semibold">{t.total}</span>
            <span className="figures text-3xl font-bold">{dollars(d.totals.total_cents)}</span>
          </div>
        </div>
      </section>

      {d.assumptions.length > 0 && (
        <section>
          <h2 className="mb-1 font-cond text-lg font-semibold">{t.assumptions}</h2>
          <ul className="list-disc space-y-1 pl-5 text-slate-soft">
            {d.assumptions.map((a, i) => <li key={i}>{view === "mine" ? a[lang] : a.customer}</li>)}
          </ul>
        </section>
      )}

      {d.invoices.length > 0 && (
        <section>
          <h2 className="mb-2 font-cond text-xl font-semibold">{t.invoices}</h2>
          <div className="slip">
            {d.invoices.map((inv) => (
              <div key={inv.id} className="slip-row flex items-center gap-3 px-4 py-3">
                <div className="flex-1">
                  <p className="font-medium">{t[inv.kind]}</p>
                  <p className={`text-sm ${inv.status === "paid" ? "text-ok" : "text-slate-soft"}`}>
                    {inv.status === "paid" ? t.paid : t.sent}
                  </p>
                </div>
                <p className="figures text-lg font-semibold">{dollars(inv.amount_cents)}</p>
                {inv.status === "sent" && (
                  <button className="font-medium text-carbon"
                    onClick={() => run(() => api.remind(inv.id)).then(() => setNotice(t.reminded))}>
                    {t.remind}
                  </button>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {error && <p className="text-flag">{error}</p>}
      {notice && <p className="text-ok" role="status">{notice}</p>}

      {d.job.status === "draft" && (
        <div className="space-y-2">
          {d.totals.needs_price > 0 && <p className="text-flag">{t.fixPrices(d.totals.needs_price)}</p>}
          <button disabled={!canSend || busy} onClick={() => run(() => api.send(id))}
            className="h-16 w-full rounded-[4px] bg-tape text-lg font-bold text-slate-ink shadow-[0_3px_0_#B8930F] disabled:bg-rule disabled:shadow-none disabled:text-slate-soft">
            {t.sendEstimate}
          </button>
        </div>
      )}
    </div>
  );
}
