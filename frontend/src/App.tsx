import { Routes, Route } from "react-router-dom";
import TopBar from "./components/layout/TopBar";
import CommandCenter from "./pages/CommandCenter";
import ReportsPage from "./pages/ReportsPage";
import AlertConsole from "./pages/AlertConsole";
import AboutPage from "./pages/AboutPage";
import InsightsPage from "./pages/InsightsPage";
import RiskDashboardPage from "./pages/RiskDashboardPage";
import RoadStatusPage from "./pages/RoadStatusPage";
import WeatherForecastPage from "./pages/WeatherForecastPage";
import EmergencyPage from "./pages/EmergencyPage";

export default function App() {
  return (
    <div className="flex h-screen flex-col">
      <TopBar />
      <Routes>
        <Route path="/" element={<CommandCenter />} />
        <Route path="/zone/:zoneId" element={<CommandCenter />} />
        <Route path="/dashboard" element={<RiskDashboardPage />} />
        <Route path="/roads" element={<RoadStatusPage />} />
        <Route path="/weather" element={<WeatherForecastPage />} />
        <Route path="/emergency" element={<EmergencyPage />} />
        <Route path="/reports" element={<ReportsPage />} />
        <Route path="/alerts" element={<AlertConsole />} />
        <Route path="/about" element={<AboutPage />} />
        <Route path="/insights" element={<InsightsPage />} />
      </Routes>
    </div>
  );
}
