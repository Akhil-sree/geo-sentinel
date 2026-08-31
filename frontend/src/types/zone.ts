export type { Zone } from "../api/zones";

export interface LandslideEvent {
  zone_id: string; event_date: string;
  type: string; trigger: string | null; source: string;
}
