import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type JobSummary } from "../api";
import { useT } from "../i18n";
import JobRow from "./JobRow";

export default function Jobs() {
  const { t } = useT();
  const [jobs, setJobs] = useState<JobSummary[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.jobs().then(setJobs).catch((e) => setError(e.message));
  }, []);

  return (
    <div className="space-y-4">
      <div className="flex items-baseline justify-between">
        <h1 className="font-cond text-3xl font-bold">{t.jobs}</h1>
        <Link to="/new" className="font-medium text-carbon">
          {t.newJob}
        </Link>
      </div>
      {error && <p className="slip p-4 text-flag">{error}</p>}
      {jobs && jobs.length === 0 && <p className="slip p-4 text-slate-soft">{t.noJobs}</p>}
      {jobs && jobs.length > 0 && (
        <div className="slip">
          {jobs.map((j) => (
            <JobRow key={j.id} job={j} />
          ))}
        </div>
      )}
    </div>
  );
}
