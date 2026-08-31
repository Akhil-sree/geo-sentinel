import { useEffect, useState } from "react";
import { getLandslides } from "../../api/zones";

interface LandslideEvent { event_date: string; type: string; source: string; zone_id: string; }

export default function EventInventory({ zoneId }: { zoneId: string }) {
  const [events, setEvents] = useState<LandslideEvent[]>([]);
  useEffect(() => {
    getLandslides().then((all: LandslideEvent[]) => setEvents(all.filter((e) => e.zone_id === zoneId))).catch(() => setEvents([]));
  }, [zoneId]);

  if (events.length === 0)
    return <p className="text-xs text-slate-500">No recorded historical events for this zone in the demo inventory.</p>;

  return (
    <ul className="space-y-1 text-xs">
      {events.map((e, i) => (
        <li key={i} className="flex justify-between">
          <span className="font-mono text-slate-400">{String(e.event_date).slice(0, 10)}</span>
          <span className="text-slate-300">{e.type}</span>
          <span className="font-mono text-[10px] text-slate-500">{e.source}</span>
        </li>
      ))}
    </ul>
  );
}
