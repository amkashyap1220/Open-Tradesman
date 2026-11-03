import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, dollars, type JobSummary, type MoneySummary } from "../api";
import { useT } from "../i18n";
import JobRow from "./JobRow";

export default function Home() {
  const { t } = useT();
  const [money, setMoney] = useState<MoneySummary | null>(null);
  const [jobs, setJobs] = useState<JobSummary[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.money().then(setMoney).catch((e) => setError(e.message));
    api.jobs().then(setJobs).catch((e) => setError(e.message));
  }, []);

  return (
    <div className="space-y-6">
      <header className="pt-2">
        <p className="text-slate-soft">{t.owed}</p>
        <p className="figures text-[64px] font-bold leading-none tracking-tight">{dollars(money?.owed_cents ?? 0)}</p>
        <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-[15px]">
          {money && money.deposits_unpaid > 0 && (
            <Link to="/money" className="font-medium text-flag">
              {t.depositsUnpaid(money.deposits_unpaid)}
            </Link>
          )}
          <span className="text-slate-soft">
            {t.paidThisMonth} <span className="figures font-semibold text-slate-ink">{dollars(money?.paid_this_month_cents ?? 0)}</span>
          </span>
        </div>
      </header>

      {error && <p className="slip p-4 text-flag">{error}</p>}

      <section>
        <h2 className="mb-2 font-cond text-xl font-semibold">{t.jobs}</h2>
        {jobs && jobs.length === 0 && <p className="slip p-4 text-slate-soft">{t.noJobs}</p>}
        {jobs && jobs.length > 0 && (
          <div className="slip">
            {jobs.slice(0, 6).map((j) => (
              <JobRow key={j.id} job={j} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
