import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API_BASE = `${BACKEND_URL}/api`;

const api = axios.create({
  baseURL: API_BASE,
  withCredentials: true,
});

// Global 401 handler: if any request comes back unauthorized (except /auth/*),
// clear the client-side session and bounce to /login. This prevents unhandled
// promise rejections from cascading through the UI when a JWT cookie expires.
api.interceptors.response.use(
  (r) => r,
  (err) => {
    const status = err?.response?.status;
    const url = err?.config?.url || "";
    if (status === 401 && !url.startsWith("/auth/")) {
      if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
        // Preserve intended destination so the user can be sent back after login
        const next = encodeURIComponent(window.location.pathname + window.location.search);
        window.location.replace(`/login?next=${next}`);
      }
    }
    return Promise.reject(err);
  }
);

export function formatApiError(detail) {
  if (detail == null) return "Something went wrong. Please try again.";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail))
    return detail
      .map((e) => (e && typeof e.msg === "string" ? e.msg : JSON.stringify(e)))
      .filter(Boolean)
      .join(" ");
  if (detail && typeof detail.msg === "string") return detail.msg;
  return String(detail);
}

export function unwrapError(err) {
  return formatApiError(err?.response?.data?.detail) || err?.message || "Unknown error";
}

export default api;
