import { NavLink, useNavigate } from "react-router-dom";
import { useT } from "../i18n";

function Tab({ to, label }: { to: string; label: string }) {
  return (
    <NavLink
      to={to}
      end={to === "/"}
      className={({ isActive }) =>
        `flex h-14 flex-1 items-center justify-center text-[15px] font-medium ${
          isActive ? "text-slate-ink underline decoration-tape decoration-[3px] underline-offset-8" : "text-slate-soft"
        }`
      }
    >
      {label}
    </NavLink>
  );
}

export default function BottomNav() {
  const { t } = useT();
  const navigate = useNavigate();
  return (
    <nav className="fixed inset-x-0 bottom-0 z-10 border-t border-rule bg-paper pb-[env(safe-area-inset-bottom)]">
      <div className="mx-auto flex max-w-xl items-center px-2 lg:max-w-3xl">
        <Tab to="/" label={t.home} />
        <Tab to="/jobs" label={t.jobs} />
        {/* The one bold thing in the chrome: start a walkthrough from anywhere. */}
        <button
          onClick={() => navigate("/new")}
          aria-label={t.newJob}
          className="-mt-8 mx-2 flex h-[72px] w-[72px] shrink-0 items-center justify-center rounded-full border-4 border-concrete bg-tape shadow-[0_2px_0_#B8930F] active:translate-y-[2px] active:shadow-none"
        >
          <svg width="28" height="28" viewBox="0 0 24 24" aria-hidden="true">
            <rect x="9" y="3" width="6" height="11" rx="3" fill="#1E2A36" />
            <path d="M6 11a6 6 0 0 0 12 0M12 17v4" stroke="#1E2A36" strokeWidth="2" fill="none" strokeLinecap="round" />
          </svg>
        </button>
        <Tab to="/money" label={t.money} />
        <Tab to="/settings" label={t.settings} />
      </div>
    </nav>
  );
}
