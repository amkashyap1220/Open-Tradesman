import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { api, dollars, type MoneySummary } from "../api";
import { useT } from "../i18n";
import { jobNo } from "./JobRow";

export default function Money() {
  const { t } = useT();
  const [m, setM] = useState<MoneySummary | null>(null);
  const [q, setQ] = useState("");
  const [answer, setAnswer] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api.money().then(setM).catch((e) => setError(e.message));
  }, []);

  async function ask(e: FormEvent) {
    e.preventDefault();
    if (!q.trim()) return;
    setBusy(true);
    setError("");
    try {
      setAnswer((await api.ask(q)).answer);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="font-cond text-3xl font-bold">{t.money}</h1>

      <form onSubmit={ask} className="slip space-y-3 p-4">
        <label className="block">
          <span className="font-cond text-lg font-semibold">{t.ask}</span>
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder={t.askPlaceholder}
            className="mt-1 w-full rounded-[4px] border border-rule px-3 py-3 text-[17px]" />
        </label>
        <button disabled={busy} className="h-12 w-full rounded-[4px] bg-slate-ink font-semibold text-paper disabled:opacity-50">
          {busy ? "…" : t.askButton}
        </button>
        {answer && <p className="border-t border-rule pt-3 text-[17px]" role="status">{answer}</p>}
      </form>

      {error && <p className="text-flag">{error}</p>}

      {m && (
        <section>
          <div className="mb-2 flex items-baseline justify-between">
            <h2 className="font-cond text-xl font-semibold">{t.openInvoices}</h2>
            <span className="figures text-xl font-bold">{dollars(m.owed_cents)}</span>
          </div>
          <div className="slip">
            {m.open_invoices.map((inv) => (
              <div key={inv.id} className="slip-row flex items-center gap-3 px-4 py-3">
                <Link to={`/jobs/${inv.job_id}`} className="min-w-0 flex-1">
                  <p className="truncate font-medium">{inv.customer}</p>
                  <p className={`figures text-sm ${inv.days_out > 14 ? "text-flag" : "text-slate-soft"}`}>
                    {jobNo(inv.job_id)} · {t[inv.kind as "deposit" | "change" | "final"]} · {t.daysOut(inv.days_out)}
                  </p>
                </Link>
                <p className="figures text-lg font-semibold">{dollars(inv.amount_cents)}</p>
                <button className="font-medium text-carbon" onClick={() => api.remind(inv.id)}>
                  {t.remind}
                </button>
              </div>
            ))}
          </div>
          {/* TODO(Nov 10): real hourly rate, profit per job, materials spend. */}
        </section>
      )}
    </div>
  );
}
