import { api } from "./client";

export interface Zone {
  id: string; name: string; district: string;
  lat: number; lng: number;
  slope: number; elevation: number;
  population: number;
  sar_acquisition_date: string | null;
  sar_change_score: number;
}

export const getZones = () => api.get<Zone[]>("/zones").then((r) => r.data);

export const getLandslides = () =>
  api.get("/landslides").then((r) => r.data);
