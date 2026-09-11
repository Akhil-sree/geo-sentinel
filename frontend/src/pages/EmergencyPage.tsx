import { useEffect, useState } from "react";
import { getEmergencyTasks, type EmergencyTask } from "../api/dashboard";
import { useUIStore } from "../store/uiStore";
import { t } from "../lib/i18n";

const PRIORITY_CONFIG: Record<string, { color: string; bg: string; icon: string }> = {
  CRITICAL: { color: "#ba1a1a", bg: "#ba1a1a15", icon: "\u26A0" },
  HIGH: { color: "#ea580c", bg: "#ea580c15", icon: "\u25B2" },
  MEDIUM: { color: "#d97706", bg: "#d9770615", icon: "\u25CF" },
  LOW: { color: "#245c45", bg: "#245c4515", icon: "\u25CB" },
};

const STATUS_CONFIG: Record<string, { color: string; bg: string; label: string }> = {
  PENDING: { color: "#d97706", bg: "#d9770615", label: "Pending" },
  IN_PROGRESS: { color: "#2563eb", bg: "#2563eb15", label: "In Progress" },
  COMPLETED: { color: "#245c45", bg: "#245c4515", label: "Completed" },
  CANCELLED: { color: "#707973", bg: "#70797315", label: "Cancelled" },
};

const TASK_TYPE_ICONS: Record<string, string> = {
  evacuation: "\u241B",
  road_clear: "\u2616",
  shelter_setup: "\u2302",
  patrol: "\u2316",
  supply: "\u2630",
};

export default function EmergencyPage() {
  const [tasks, setTasks] = useState<EmergencyTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>("ACTIVE");
  const selectZone = useUIStore((s) => s.selectZone);

  useEffect(() => {
    getEmergencyTasks()
      .then((r) => setTasks(r.tasks))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const activeTasks = tasks.filter((t) => t.status !== "COMPLETED" && t.status !== "CANCELLED");
  const filtered = filter === "ALL" ? tasks
    : filter === "ACTIVE" ? activeTasks
    : tasks.filter((t) => t.priority === filter);

  const criticalCount = activeTasks.filter((t) => t.priority === "CRITICAL").length;
  const highCount = activeTasks.filter((t) => t.priority === "HIGH").length;

  if (loading) {
    return (
      <div className="flex flex-1 items-center justify-center bg-[#f0eee6]">
        <div className="text-center">
          <div className="mx-auto mb-3 h-8 w-8 animate-spin rounded-full border-2 border-[#ba1a1a] border-t-transparent" />
          <p className="text-[11px] text-[#707973]">Loading emergency tasks...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col overflow-y-auto bg-[#f0eee6]">
      {/* Header */}
      <div className="border-b border-[#ba1a1a]/20 bg-gradient-to-r from-[#ba1a1a] to-[#991b1b] px-5 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-white/20 text-white">
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                <path d="M10 2L2 18h16L10 2z" stroke="white" strokeWidth="1.5" fill="none"/>
                <path d="M10 7v6M10 15.5v0" stroke="white" strokeWidth="1.5" strokeLinecap="round"/>
              </svg>
            </span>
            <div>
              <h1 className="text-lg font-bold text-white">{t("emergencyPriority")}</h1>
              <p className="text-[10px] text-white/70">
                Active response tasks and deployment status
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {criticalCount > 0 && (
              <div className="rounded-lg bg-white/20 px-3 py-1.5 text-center">
                <p className="text-xl font-bold text-white">{criticalCount}</p>
                <p className="text-[8px] font-bold text-white/80">CRITICAL</p>
              </div>
            )}
            {highCount > 0 && (
              <div className="rounded-lg bg-white/20 px-3 py-1.5 text-center">
                <p className="text-xl font-bold text-white">{highCount}</p>
                <p className="text-[8px] font-bold text-white/80">HIGH</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Filter tabs */}
      <div className="flex border-b border-[#d9e2d9] bg-white px-5">
        {(["ACTIVE", "CRITICAL", "HIGH", "ALL"] as const).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-4 py-2 text-[10px] font-bold uppercase tracking-wide transition-colors ${
              filter === f
                ? "border-b-2 border-[#ba1a1a] text-[#ba1a1a]"
                : "text-[#707973] hover:text-[#1b1c17]"
            }`}
          >
            {f}
            {f === "ACTIVE" && ` (${activeTasks.length})`}
          </button>
        ))}
      </div>

      {/* Task list */}
      <div className="space-y-2 px-5 py-3">
        {filtered.length === 0 ? (
          <div className="rounded-lg border border-[#d9e2d9] bg-white p-8 text-center">
            <p className="text-[11px] text-[#707973]">No tasks match filter.</p>
          </div>
        ) : (
          filtered.map((task) => {
            const prio = PRIORITY_CONFIG[task.priority] || PRIORITY_CONFIG.MEDIUM;
            const stat = STATUS_CONFIG[task.status] || STATUS_CONFIG.PENDING;
            const typeIcon = TASK_TYPE_ICONS[task.task_type] || "\u2022";

            return (
              <div
                key={task.id}
                className="overflow-hidden rounded-lg border border-[#d9e2d9] bg-white shadow-sm transition hover:shadow-md"
              >
                <div className="flex items-stretch">
                  {/* Priority indicator */}
                  <div
                    className="w-1.5 shrink-0"
                    style={{ backgroundColor: prio.color }}
                  />

                  <div className="flex-1 p-3">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        {/* Title + badges */}
                        <div className="flex items-center gap-2">
                          <span className="text-sm">{typeIcon}</span>
                          <h3 className="text-[11px] font-bold text-[#1b1c17]">
                            {task.title}
                          </h3>
                        </div>

                        {/* Description */}
                        <p className="mt-1 text-[9px] leading-relaxed text-[#707973]">
                          {task.description}
                        </p>

                        {/* Meta row */}
                        <div className="mt-2 flex flex-wrap items-center gap-2">
                          <span
                            className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[8px] font-bold"
                            style={{ backgroundColor: prio.bg, color: prio.color, border: `1px solid ${prio.color}30` }}
                          >
                            {prio.icon} {task.priority}
                          </span>
                          <span
                            className="rounded-full px-2 py-0.5 text-[8px] font-bold"
                            style={{ backgroundColor: stat.bg, color: stat.color }}
                          >
                            {stat.label}
                          </span>
                          <span className="text-[8px] text-[#707973]">
                            Zone: <span className="font-bold text-[#1b1c17]">{task.zone_id}</span>
                          </span>
                          {task.assigned_team && (
                            <span className="text-[8px] text-[#707973]">
                              Team: <span className="font-bold text-[#1b1c17]">{task.assigned_team}</span>
                            </span>
                          )}
                          {task.estimated_time && task.estimated_time !== "\u2014" && (
                            <span className="text-[8px] text-[#707973]">
                              ETA: <span className="font-bold text-[#1b1c17]">{task.estimated_time}</span>
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Zone button */}
                      <button
                        onClick={() => selectZone(task.zone_id)}
                        className="ml-3 shrink-0 rounded border border-[#d9e2d9] px-2 py-1 text-[8px] font-bold text-[#04442f] transition hover:bg-[#04442f] hover:text-white"
                      >
                        View Zone
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
