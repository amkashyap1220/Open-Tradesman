import { Navigate, Route, Routes } from "react-router-dom";
import BottomNav from "./components/BottomNav";
import Home from "./pages/Home";
import Jobs from "./pages/Jobs";
import NewJob from "./pages/NewJob";
import JobDetail from "./pages/JobDetail";
import Money from "./pages/Money";
import Settings from "./pages/Settings";

export default function App() {
  return (
    <div className="min-h-dvh font-sans">
      {/* Phone: one column. Laptop: same app, centered and wider for demos. */}
      <main className="mx-auto max-w-xl px-4 pb-32 pt-[max(1.25rem,env(safe-area-inset-top))] lg:max-w-3xl">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/jobs" element={<Jobs />} />
          <Route path="/new" element={<NewJob />} />
          <Route path="/jobs/:id" element={<JobDetail />} />
          <Route path="/money" element={<Money />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
      <BottomNav />
    </div>
  );
}
