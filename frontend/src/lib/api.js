import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API_BASE = `${BACKEND_URL}/api`;

const api = axios.create({
  baseURL: API_BASE,
  withCredentials: true,
});

// On 401 from any non-/auth endpoint, silently re-authenticate as guest and retry.
// This keeps the app usable without ever showing a login screen.
let guestPromise = null;
api.interceptors.response.use(
  (r) => r,
  async (err) => {
    const status = err?.response?.status;
    const cfg = err?.config || {};
    const url = cfg.url || "";
    if (status === 401 && !url.startsWith("/auth/") && !cfg.__retried) {
      cfg.__retried = true;
      try {
        if (!guestPromise) {
          guestPromise = api.post("/auth/guest").finally(() => { guestPromise = null; });
        }
        await guestPromise;
        return api.request(cfg);
      } catch { /* fall through to reject */ }
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
