import { Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/layout/Layout";
import { Dashboard } from "./pages/Dashboard";
import { Connections } from "./pages/Connections";
import { ConnectionForm } from "./pages/ConnectionForm";
import { Pipelines } from "./pages/Pipelines";
import { PipelineForm } from "./pages/PipelineForm";
import { Jobs } from "./pages/Jobs";
import { JobDetail } from "./pages/JobDetail";
import { Settings } from "./pages/Settings";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/connections" element={<Connections />} />
        <Route path="/connections/new" element={<ConnectionForm />} />
        <Route path="/connections/:id" element={<ConnectionForm />} />
        <Route path="/pipelines" element={<Pipelines />} />
        <Route path="/pipelines/new" element={<PipelineForm />} />
        <Route path="/pipelines/:id" element={<PipelineForm />} />
        <Route path="/jobs" element={<Jobs />} />
        <Route path="/jobs/:id" element={<JobDetail />} />
        <Route path="/settings" element={<Settings />} />
      </Route>
    </Routes>
  );
}
