import { useEffect, useState } from "react";
import { getEmergencyTasks } from "../../api/dashboard";
import Spinner from "../common/Spinner";
import type { EmergencyTask } from "../../types/risk";

const PRIORITY_COLORS: Record<string, string> = {
  CRITICAL: "#ba1a1a",
  HIGH: "#ea580c",
  MEDIUM: "#d97706",
  LOW: "#2563EB",
};

const STATUS_COLORS: Record<string, string> = {
  PENDING: "#d97706",
  IN_PROGRESS: "#ea580c",
  COMPLETED: "#2563EB",
};

const TASK_ICONS: Record<string, string> = {
  evacuation: "🚨",
  road_clear: "🚧",
  shelter_setup: "🏠",
  patrol: "👮",
  supply: "📦",
};

export default function EmergencyTasksPanel() {
  const [tasks, setTasks] = useState<EmergencyTask[]>([]);
  const [stats, setStats] = useState({ critical_pending: 0, in_progress: 0, completed: 0 });
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState<string>("all");

  useEffect(() => {
    setLoading(true);
    getEmergencyTasks()
      .then((data) => {
        setTasks(data.tasks || []);
        setStats({ critical_pending: data.critical_pending, in_progress: data.in_progress, completed: data.completed });
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="rounded-card p-4" style={{ background: 'rgba(229, 233, 224, 0.45)', backdropFilter: 'blur(8px)', border: '1px solid rgba(255,255,255,0.18)' }}>
        <div className="flex items-center gap-2 text-[14px] text-gs-text-secondary"><Spinner /> Loading tasks...</div>
      </div>
    );
  }

  if (!tasks.length) return null;

  const filtered = filter === "all" ? tasks : tasks.filter((t) => t.status === filter);

  return (
    <div className="rounded-card p-4" style={{ background: 'rgba(229, 233, 224, 0.45)', backdropFilter: 'blur(8px)', border: '1px solid rgba(255,255,255,0.18)' }}>
      <h3 className="text-[15px] font-bold text-gs-text mb-1">Emergency Tasks</h3>
      <p className="text-[12px] text-gs-text-secondary mb-3">
        {stats.critical_pending} critical pending · {stats.in_progress} in progress · {stats.completed} completed
      </p>

      {/* Filter tabs */}
      <div className="flex gap-1 mb-3">
        {["all", "PENDING", "IN_PROGRESS", "COMPLETED"].map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-2 py-1 rounded-md text-[11px] font-medium transition ${
              filter === f ? 'bg-forest text-white' : 'bg-white/40 text-gs-text-secondary hover:bg-white/60'
            }`}
          >
            {f === "all" ? "All" : f.replace("_", " ")}
          </button>
        ))}
      </div>

      {/* Task list */}
      <div className="space-y-2 max-h-80 overflow-y-auto">
        {filtered.map((task) => (
          <div key={task.id} className="rounded-lg p-3" style={{ background: 'rgba(255,255,255,0.35)', borderLeft: `3px solid ${PRIORITY_COLORS[task.priority] || '#999'}` }}>
            <div className="flex items-center justify-between mb-1">
              <div className="flex items-center gap-2">
                <span className="text-[16px]">{TASK_ICONS[task.task_type] || "📋"}</span>
                <span className="text-[13px] font-semibold text-gs-text">{task.title}</span>
              </div>
              <div className="flex items-center gap-1">
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold text-white" style={{ background: PRIORITY_COLORS[task.priority] }}>
                  {task.priority}
                </span>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold text-white" style={{ background: STATUS_COLORS[task.status] }}>
                  {task.status.replace("_", " ")}
                </span>
              </div>
            </div>
            <p className="text-[11px] text-gs-text-secondary mb-1">{task.description}</p>
            <div className="flex items-center gap-3 text-[10px] text-gs-text-secondary">
              {task.assigned_team && <span>Team: {task.assigned_team}</span>}
              {task.estimated_time && <span>ETA: {task.estimated_time}</span>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
