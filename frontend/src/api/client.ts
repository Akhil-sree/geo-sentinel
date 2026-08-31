import axios from "axios";

export const api = axios.create({
  baseURL: "/api",
  timeout: 20000,
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error(
      "API error:",
      error.config?.url,
      error.message,
    );

    return Promise.reject(error);
  },
);