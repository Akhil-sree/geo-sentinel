import { useEffect, useState } from "react";
import { getRiskIntensification, getEmergencyPriorities } from "../api/risk";
import { getEmergencyTasks } from "../api/dashboard";
import { getLandslides } from "../api/zones";
import { useUIStore } from "../store/uiStore";
import Spinner from "../components/common/Spinner";
import type { EmergencyPriority, EmergencyTask, IntensificationResult } from "../types/risk";

export default function EmergencyAlertsPage() {
  const simTime = useUIStore((s) => s.simTime);
  const [priorities, setPriorities] = useState<EmergencyPriority[]>([]);
  const [intensification, setIntensification] = useState<IntensificationResult[]>([]);
  const [tasks, setTasks] = useState<EmergencyTask[]>([]);
  const [landslides, setLandslides] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState<"priorities" | "intensification" | "tasks" | "events">("priorities");
  const [taskFilter, setTaskFilter] = useState<string>("all");

  useEffect(() => {
    setLoading(true);
    Promise.all([
      getEmergencyPriorities(simTime).catch(() => ({ priorities: [] })),
      getRiskIntensification(simTime).catch(() => ({ intensification: [] })),
      getEmergencyTasks().catch(() => ({ tasks: [] })),
      getLandslides().catch(() => []),
    ]).then(([p, inc, t, ev]) => {
      setPriorities(p.priorities || []);
      setIntensification(inc.intensification || []);
      setTasks(t.tasks || []);
      setLandslides(ev);
    }).finally(() => setLoading(false));
  }, [simTime]);

  const criticalCount = priorities.filter((p) => p.tier === "CRITICAL").length;
  const highCount = priorities.filter((p) => p.tier === "HIGH").length;
  const escalatedCount = priorities.filter((p) => p.escalated).length;

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

  const filteredTasks = taskFilter === "all" ? tasks : tasks.filter((t) => t.status === taskFilter);

  return (
    <div className="flex flex-1 flex-col overflow-y-auto p-6" style={{ background: '#F4F5F0' }}>
      <div className="mx-auto w-full max-w-5xl">
        <div className="mb-6">
          <h1 className="text-[28px] font-bold" style={{ color: '#1A3C2E' }}>Emergency Alerts & Response</h1>
          <p className="text-[14px] mt-1" style={{ color: '#6B7280' }}>Emergency prioritization, risk intensification tracking, tasks, and landslide event history</p>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <Spinner /><span className="ml-3 text-[16px]" style={{ color: '#6B7280' }}>Loading...</span>
          </div>
        ) : (
          <>
            {/* Summary Cards */}
            <div className="grid grid-cols-4 gap-4 mb-6">
              <div className="rounded-xl p-4" style={{ background: '#FFFFFF', border: '1px solid #E5E7EB' }}>
                <div className="text-[28px] font-bold" style={{ color: '#ba1a1a' }}>{criticalCount}</div>
                <div className="text-[13px]" style={{ color: '#6B7280' }}>Critical Zones</div>
              </div>
              <div className="rounded-xl p-4" style={{ background: '#FFFFFF', border: '1px solid #E5E7EB' }}>
                <div className="text-[28px] font-bold" style={{ color: '#ea580c' }}>{highCount}</div>
                <div className="text-[13px]" style={{ color: '#6B7280' }}>High Priority</div>
              </div>
              <div className="rounded-xl p-4" style={{ background: '#FFFFFF', border: '1px solid #E5E7EB' }}>
                <div className="text-[28px] font-bold" style={{ color: '#d97706' }}>{escalatedCount}</div>
                <div className="text-[13px]" style={{ color: '#6B7280' }}>Escalated</div>
              </div>
              <div className="rounded-xl p-4" style={{ background: '#FFFFFF', border: '1px solid #E5E7EB' }}>
                <div className="text-[28px] font-bold" style={{ color: '#1A3C2E' }}>{landslides.length}</div>
                <div className="text-[13px]" style={{ color: '#6B7280' }}>Past Events</div>
              </div>
            </div>

            {/* Tab Toggle */}
            <div className="flex gap-2 mb-6">
              {(["priorities", "intensification", "tasks", "events"] as const).map((t) => (
                <button key={t} onClick={() => setTab(t)}
                  className="px-5 py-2.5 rounded-lg text-[14px] font-semibold transition capitalize"
                  style={{
                    background: tab === t ? '#1A3C2E' : '#FFFFFF',
                    color: tab === t ? '#FFFFFF' : '#6B7280',
                    border: tab === t ? '1px solid #1A3C2E' : '1px solid #E5E7EB',
                  }}>
                  {t === "priorities" ? `Zone Priorities (${priorities.length})` : t === "intensification" ? `Intensification (${intensification.length})` : t === "tasks" ? `Tasks (${tasks.length})` : `Landslide Events (${landslides.length})`}
                </button>
              ))}
            </div>

            {/* Priorities Tab — from backend /risk/emergency-priorities */}
            {tab === "priorities" && (
              <div className="space-y-3">
                {priorities.length === 0 ? (
                  <div className="rounded-xl p-8 text-center" style={{ background: '#FFFFFF', border: '1px solid #E5E7EB' }}>
                    <p className="text-[16px] font-medium" style={{ color: '#6B7280' }}>No priority data available</p>
                  </div>
                ) : priorities.map((p) => (
                  <div key={p.zone_id} className="rounded-xl p-4" style={{ background: '#FFFFFF', border: '1px solid #E5E7EB', borderLeft: `4px solid ${p.tier_color}` }}>
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-3">
                        <span className="text-[20px] font-bold" style={{ color: '#1A3C2E' }}>#{p.rank}</span>
                        <div>
                          <h4 className="text-[15px] font-bold" style={{ color: '#1A3C2E' }}>{p.name}</h4>
                          <p className="text-[12px]" style={{ color: '#6B7280' }}>{p.district}</p>
                        </div>
                      </div>
                      <span className="px-3 py-1 rounded-full text-[12px] font-bold text-white" style={{ background: p.tier_color }}>{p.tier}</span>
                    </div>
                    <div className="grid grid-cols-5 gap-4 mt-3">
                      <div>
                        <div className="text-[11px]" style={{ color: '#6B7280' }}>Risk</div>
                        <div className="text-[16px] font-bold" style={{ color: p.tier_color }}>{(p.risk_score * 100).toFixed(0)}%</div>
                      </div>
                      <div>
                        <div className="text-[11px]" style={{ color: '#6B7280' }}>Population</div>
                        <div className="text-[16px] font-bold" style={{ color: '#1A3C2E' }}>{p.population.toLocaleString()}</div>
                      </div>
                      <div>
                        <div className="text-[11px]" style={{ color: '#6B7280' }}>Response</div>
                        <div className="text-[14px] font-bold" style={{ color: '#1A3C2E' }}>{p.response_time}</div>
                      </div>
                      <div>
                        <div className="text-[11px]" style={{ color: '#6B7280' }}>Slope</div>
                        <span className="px-2 py-0.5 rounded-full text-[11px] font-bold text-white" style={{ background: p.slope_state_color }}>{p.slope_state_label}</span>
                      </div>
                      <div>
                        <div className="text-[11px]" style={{ color: '#6B7280' }}>Evacuation</div>
                        <span className="px-2 py-0.5 rounded-full text-[11px] font-medium" style={{ background: p.evac_color + '20', color: p.evac_color }}>{p.evac_status}</span>
                      </div>
                    </div>
                    {p.escalated && <div className="mt-2 inline-block px-2 py-0.5 rounded text-[10px] font-bold text-white" style={{ background: '#ba1a1a' }}>ESCALATED</div>}
                  </div>
                ))}
              </div>
            )}

            {/* Intensification Tab */}
            {tab === "intensification" && (
              <div className="space-y-3">
                {intensification.map((inc) => (
                  <div key={inc.zone_id} className="rounded-xl p-4 flex items-center justify-between" style={{ background: '#FFFFFF', border: '1px solid #E5E7EB', borderLeft: `4px solid ${inc.color}` }}>
                    <div>
                      <h4 className="text-[15px] font-bold" style={{ color: '#1A3C2E' }}>{inc.name}</h4>
                      <p className="text-[12px]" style={{ color: '#6B7280' }}>
                        Risk: {(inc.current_risk * 100).toFixed(0)}%
                        {inc.previous_risk != null && ` → was ${(inc.previous_risk * 100).toFixed(0)}%`}
                      </p>
                    </div>
                    <div className="text-right">
                      <span className="px-3 py-1 rounded-full text-[12px] font-bold text-white" style={{ background: inc.color }}>{inc.rate}</span>
                      <div className="text-[12px] mt-1 font-medium" style={{ color: inc.color }}>
                        {inc.change > 0 ? '+' : ''}{(inc.change * 100).toFixed(1)}%
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Tasks Tab — from backend /emergency/tasks */}
            {tab === "tasks" && (
              <div className="space-y-3">
                {tasks.length === 0 ? (
                  <div className="rounded-xl p-8 text-center" style={{ background: '#FFFFFF', border: '1px solid #E5E7EB' }}>
                    <p className="text-[16px] font-medium" style={{ color: '#6B7280' }}>No emergency tasks assigned</p>
                  </div>
                ) : (
                  <>
                    <div className="flex gap-1 mb-3">
                      {["all", "PENDING", "IN_PROGRESS", "COMPLETED"].map((f) => (
                        <button
                          key={f}
                          onClick={() => setTaskFilter(f)}
                          className={`px-3 py-1.5 rounded-md text-[12px] font-medium transition`}
                          style={{
                            background: taskFilter === f ? '#1A3C2E' : '#FFFFFF',
                            color: taskFilter === f ? '#FFFFFF' : '#6B7280',
                            border: taskFilter === f ? '1px solid #1A3C2E' : '1px solid #E5E7EB',
                          }}
                        >
                          {f === "all" ? "All" : f.replace("_", " ")}
                        </button>
                      ))}
                    </div>
                    {filteredTasks.map((task) => (
                      <div key={task.id} className="rounded-xl p-4" style={{ background: '#FFFFFF', border: '1px solid #E5E7EB', borderLeft: `4px solid ${PRIORITY_COLORS[task.priority] || '#999'}` }}>
                        <div className="flex items-center justify-between mb-1">
                          <div className="flex items-center gap-2">
                            <span className="text-[16px]">{TASK_ICONS[task.task_type] || "📋"}</span>
                            <span className="text-[14px] font-semibold" style={{ color: '#1A3C2E' }}>{task.title}</span>
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
                        <p className="text-[12px] mt-1" style={{ color: '#6B7280' }}>{task.description}</p>
                        <div className="flex items-center gap-3 mt-2 text-[11px]" style={{ color: '#6B7280' }}>
                          {task.assigned_team && <span>Team: {task.assigned_team}</span>}
                          {task.estimated_time && <span>ETA: {task.estimated_time}</span>}
                          {task.zone_id && <span>Zone: {task.zone_id}</span>}
                        </div>
                      </div>
                    ))}
                  </>
                )}
              </div>
            )}

            {/* Landslide Events Tab */}
            {tab === "events" && (
              <div className="space-y-3">
                {landslides.length === 0 ? (
                  <div className="rounded-xl p-8 text-center" style={{ background: '#FFFFFF', border: '1px solid #E5E7EB' }}>
                    <p className="text-[16px] font-medium" style={{ color: '#6B7280' }}>No landslide events recorded</p>
                  </div>
                ) : (
                  landslides.map((ev, i) => (
                    <div key={i} className="rounded-xl p-4 flex items-center justify-between" style={{ background: '#FFFFFF', border: '1px solid #E5E7EB' }}>
                      <div className="flex items-center gap-3">
                        <span className="text-[20px]">⚠️</span>
                        <div>
                          <h4 className="text-[14px] font-bold" style={{ color: '#1A3C2E' }}>{ev.type}</h4>
                          <p className="text-[12px]" style={{ color: '#6B7280' }}>{ev.zone_id} · {new Date(ev.event_date).toLocaleDateString("en-IN", { year: "numeric", month: "short", day: "numeric" })}</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <span className="text-[12px] font-medium" style={{ color: '#6B7280' }}>{ev.trigger || "Unknown trigger"}</span>
                        <div className="text-[11px]" style={{ color: '#9CA3AF' }}>{ev.source}</div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
