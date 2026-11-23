// ============================================================
// api.js — ONE place that talks to the backend
// ------------------------------------------------------------
// Before: Login.js, Register.js and Dashboard.js each built
// their own fetch() calls, each repeated the Authorization
// header, and each handled 401 slightly differently.
//
// Now every request goes through apiFetch(), which:
//   1. Prefixes the backend URL (REACT_APP_API_URL)
//   2. Attaches the JWT ("Authorization: Bearer <token>")
//   3. Sends/parses JSON
//   4. On 401 (expired/invalid token): clears the token and
//      sends the user to the login page — in ONE place
//   5. Throws an ApiError with FastAPI's "detail" message so
//      pages can just do: try { ... } catch (e) { setError(e.message) }
//
// This is the DRY principle (Don't Repeat Yourself) and the
// "single point of change": if we ever move from localStorage
// to cookies, only this file changes.
// ============================================================

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000'
const TOKEN_KEY = 'token'

export function getToken() {
    return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token) {
    localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken() {
    localStorage.removeItem(TOKEN_KEY)
}

// A custom error type so callers can check err.status (e.g. 429)
export class ApiError extends Error {
    constructor(message, status) {
        super(message)
        this.status = status
    }
}

// FastAPI returns errors as {detail: "text"} OR, for validation
// errors (422), {detail: [{msg: "...", loc: [...]}, ...]}.
// This turns either shape into one readable sentence.
function readableDetail(data, fallback) {
    if (!data || !data.detail) return fallback
    if (typeof data.detail === 'string') return data.detail
    if (Array.isArray(data.detail)) {
        return data.detail.map(d => d.msg).join('. ')
    }
    return fallback
}

export async function apiFetch(path, { method = 'GET', body, auth = true } = {}) {
    const headers = {}
    if (body !== undefined) headers['Content-Type'] = 'application/json'

    if (auth) {
        const token = getToken()
        if (token) headers['Authorization'] = `Bearer ${token}`
    }

    let response
    try {
        response = await fetch(`${API_URL}${path}`, {
            method,
            headers,
            body: body !== undefined ? JSON.stringify(body) : undefined,
        })
    } catch (networkError) {
        // fetch() only rejects on network failure (server down,
        // CORS blocked, offline) — NOT on 4xx/5xx responses.
        throw new ApiError(
            'Could not reach the server. If it was idle, the free-tier backend can take ~30-60s to wake up — try again.',
            0
        )
    }

    // Some endpoints (e.g. DELETE) may return an empty body
    const text = await response.text()
    let data = null
    let notJson = false
    try {
        data = text ? JSON.parse(text) : null
    } catch {
        // Not JSON — e.g. Render's HTML "waking up" / 502 page.
        // Without this, users would see "Unexpected token '<'".
        notJson = true
    }

    if (response.status === 401 && auth) {
        // Token expired or invalid → log out everywhere at once
        clearToken()
        if (window.location.pathname !== '/') window.location.assign('/')
        throw new ApiError('Your session expired. Please sign in again.', 401)
    }

    if (!response.ok) {
        const message = notJson
            ? 'The server is starting up or temporarily unavailable. Try again in a few seconds.'
            : readableDetail(data, `Request failed (${response.status})`)
        throw new ApiError(message, response.status)
    }

    return data
}

// ------------------------------------------------------------
// Named helpers — pages call these instead of raw URLs, so the
// list of everything the frontend can ask the backend for lives
// right here and reads like a table of contents.
// ------------------------------------------------------------
export const api = {
    // Auth
    login: (email, password) => apiFetch('/login', { method: 'POST', body: { email, password }, auth: false }),
    register: (email, username, password) => apiFetch('/register', { method: 'POST', body: { email, username, password }, auth: false }),
    me: () => apiFetch('/me'),
    saveLocation: (location_label) => apiFetch('/me/location', { method: 'PUT', body: { location_label } }),

    // Applications
    listApplications: () => apiFetch('/applications'),
    createApplication: (app) => apiFetch('/applications', { method: 'POST', body: app }),
    updateApplication: (id, changes) => apiFetch(`/applications/${id}`, { method: 'PUT', body: changes }),
    deleteApplication: (id) => apiFetch(`/applications/${id}`, { method: 'DELETE' }),

    // Location + jobs
    // POST with a JSON body (not ?lat=&lng= in the URL) so a
    // location or home address never ends up in server access logs.
    resolveCoords: (lat, lng) => apiFetch('/location/resolve', { method: 'POST', body: { lat, lng } }),
    resolveQuery: (q) => apiFetch('/location/resolve', { method: 'POST', body: { q } }),
    searchJobs: ({ q, location, radius_km }) => {
        const params = new URLSearchParams({ q, location, radius_km: String(radius_km) })
        return apiFetch(`/jobs/search?${params}`)
    },

    // Email tracking
    emailStatus: () => apiFetch('/email/status'),
    emailConnectUrl: () => apiFetch('/email/connect'),
    emailOAuthComplete: (code, state) => apiFetch('/email/oauth/complete', { method: 'POST', body: { code, state } }),
    emailSync: () => apiFetch('/email/sync', { method: 'POST' }),
    emailDisconnect: () => apiFetch('/email/connection', { method: 'DELETE' }),

    // Notifications
    notifications: () => apiFetch('/notifications'),
    unreadCount: () => apiFetch('/notifications/unread-count'),
    markRead: (id) => apiFetch(`/notifications/${id}/read`, { method: 'POST' }),
    markAllRead: () => apiFetch('/notifications/read-all', { method: 'POST' }),
    applySuggestion: (id) => apiFetch(`/notifications/${id}/apply`, { method: 'POST' }),
    dismissSuggestion: (id) => apiFetch(`/notifications/${id}/dismiss`, { method: 'POST' }),
}
