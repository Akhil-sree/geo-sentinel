import { Suspense, lazy } from "react";
import { Routes, Route } from "react-router-dom";
import TopBar from "./components/layout/TopBar";
import BackendStatusBanner from "./components/layout/BackendStatusBanner";

// Route-level code splitting (P3): the command center loads first;
// secondary pages load on navigation. Each is a separate chunk.
const CommandCenter = lazy(() => import("./pages/CommandCenter"));
const ReportsPage = lazy(() => import("./pages/ReportsPage"));
const AlertConsole = lazy(() => import("./pages/AlertConsole"));
const RoadConnectivityPage = lazy(() => import("./pages/RoadConnectivityPage"));
const WeatherForecastPage = lazy(() => import("./pages/WeatherForecastPage"));
const EmergencyAlertsPage = lazy(() => import("./pages/EmergencyAlertsPage"));
const InsightsPage = lazy(() => import("./pages/InsightsPage"));
const AboutPage = lazy(() => import("./pages/AboutPage"));
const SensorsPage = lazy(() => import("./pages/SensorsPage"));
const SatellitePage = lazy(() => import("./pages/SatellitePage"));
const SystemHealthPage = lazy(() => import("./pages/SystemHealthPage"));
const DatasetDashboardPage = lazy(() => import("./pages/DatasetDashboardPage"));

export default function App() {
  return (
    <div className="flex h-screen flex-col">
      <TopBar />
      <BackendStatusBanner />
      <Suspense
        fallback={
          <div style={{ padding: 24, fontSize: 14, opacity: 0.7 }}>
            Loading view…
          </div>
        }
      >
        <Routes>
          <Route path="/" element={<CommandCenter />} />
          <Route path="/zone/:zoneId" element={<CommandCenter />} />
          <Route path="/reports" element={<ReportsPage />} />
          <Route path="/alerts" element={<AlertConsole />} />
          <Route path="/roads" element={<RoadConnectivityPage />} />
          <Route path="/weather" element={<WeatherForecastPage />} />
          <Route path="/emergency" element={<EmergencyAlertsPage />} />
          <Route path="/insights" element={<InsightsPage />} />
          <Route path="/about" element={<AboutPage />} />
          <Route path="/sensors" element={<SensorsPage />} />
          <Route path="/satellite" element={<SatellitePage />} />
          <Route path="/health" element={<SystemHealthPage />} />
          <Route path="/data" element={<DatasetDashboardPage />} />
        </Routes>
      </Suspense>
    </div>
  );
}
