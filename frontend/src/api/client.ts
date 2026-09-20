import axios from "axios";
import { useApiStatus } from "../store/apiStatus";

/**
 * API base URL resolution (no rebuild needed for same-origin deploys):
 * - VITE_API_BASE_URL when set (e.g. https://api.example.com/api or /api)
 * - otherwise the same-origin relative "/api" (dev proxy + compose nginx)
 */
export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.trim() || "/api";

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 20000,
});

api.interceptors.response.use(
  (response) => {
    useApiStatus.getState().reportSuccess();
    return response;
  },
  (error) => {
    const status: number | undefined = error.response?.status;
    // 404 = reachable backend answering "not found" — NOT a connectivity
    // failure, so it must not flip the global banner to BACKEND UNAVAILABLE.
    if (status === undefined || status === 0 || status >= 500) {
      useApiStatus.getState().reportFailure({
        url: error.config?.url,
        status,
      });
    }
    console.error(
      "API error:",
      error.config?.url,
      error.message,
    );

    return Promise.reject(error);
  },
);
