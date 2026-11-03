import { Link } from "react-router-dom";
import { dollars, type JobSummary } from "../api";
import { useT } from "../i18n";

export const jobNo = (id: number) => `No. ${String(id).padStart(4, "0")}`;

export default function JobRow({ job }: { job: JobSummary }) {
  const { t } = useT();
  return (
    <Link to={`/jobs/${job.id}`} className="slip-row flex items-center gap-3 px-4 py-3 active:bg-concrete">
      <div className="min-w-0 flex-1">
        <p className="figures text-sm text-slate-soft">{jobNo(job.id)}</p>
        <p className="truncate text-[17px] font-medium">{job.title || job.customer_name}</p>
        <p className="text-sm text-slate-soft">
          {job.customer_name} · {t.status[job.status] ?? job.status}
        </p>
      </div>
      <p className="figures text-xl font-semibold">{dollars(job.total_cents)}</p>
    </Link>
  );
}
