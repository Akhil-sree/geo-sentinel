import { Routes, Route } from "react-router-dom";
import TopBar from "./components/layout/TopBar";
import CommandCenter from "./pages/CommandCenter";
import ReportsPage from "./pages/ReportsPage";
import AlertConsole from "./pages/AlertConsole";
import AboutPage from "./pages/AboutPage";

export default function App() {
  return (
    <div className="flex h-screen flex-col">
      <TopBar />
      <Routes>
        <Route path="/" element={<CommandCenter />} />
        <Route path="/zone/:zoneId" element={<CommandCenter />} />
        <Route path="/reports" element={<ReportsPage />} />
        <Route path="/alerts" element={<AlertConsole />} />
        <Route path="/about" element={<AboutPage />} />
      </Routes>
    </div>
  );
}
