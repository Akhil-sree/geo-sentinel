import { api } from "./client";

export const getSensors = () => api.get("/sensors").then((r) => r.data);
export const getSatStatus = () => api.get("/satellite/status").then((r) => r.data);
export const getSatScenes = () => api.get("/satellite/scenes").then((r) => r.data);
export const getMetrics = () => api.get("/metrics").then((r) => r.data);
export const getExposure = () => api.get("/exposure/villages").then((r) => r.data);
export const getInventory = () => api.get("/landslides/inventory").then((r) => r.data);
export const getRainWindows = (zone: string) =>
  api.get(`/risk/${zone}/rainfall-windows`).then((r) => r.data);
export const getAlertLangs = () => api.get("/alerts/languages").then((r) => r.data);
export const getModelVersions = () => api.get("/models").then((r) => r.data);
export const getDatasets = () => api.get("/datasets").then((r) => r.data);
export const getDataset = (v: string) => api.get(`/datasets/${v}`).then((r) => r.data);
export const getTemporal = () => api.get("/landslides/temporal").then((r) => r.data);
export const getSpatial = () => api.get("/landslides/spatial").then((r) => r.data);
export const getDataQuality = () => api.get("/data-quality").then((r) => r.data);
