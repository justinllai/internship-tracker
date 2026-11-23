// ============================================================
// Frontend tests (run: npm test)
// We test behavior a user or another developer relies on:
//   - logged-out users get sent to the login page
//   - the API wrapper logs you out on a 401
//   - small helpers return what the UI expects
// fetch is mocked, so no backend is needed.
// ============================================================

import { render, screen } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import ProtectedRoute from './components/ProtectedRoute'
import Login from './pages/Login'
import { apiFetch, setToken, getToken, ApiError } from './api'
import { logoColor, timeAgo } from './constants'

afterEach(() => {
    localStorage.clear()
    jest.restoreAllMocks()
})

test('protected pages redirect to login when there is no token', () => {
    render(
        <MemoryRouter initialEntries={['/dashboard']}>
            <Routes>
                <Route path="/" element={<p>login page</p>} />
                <Route path="/dashboard" element={<ProtectedRoute><p>secret tracker</p></ProtectedRoute>} />
            </Routes>
        </MemoryRouter>
    )
    expect(screen.getByText('login page')).toBeInTheDocument()
    expect(screen.queryByText('secret tracker')).not.toBeInTheDocument()
})

test('login page renders labelled fields', () => {
    render(<MemoryRouter><Login /></MemoryRouter>)
    // getByLabelText only works if <label htmlFor> is wired up — an accessibility check
    expect(screen.getByLabelText('Email')).toBeInTheDocument()
    expect(screen.getByLabelText('Password')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
})

test('apiFetch sends the bearer token and returns JSON', async () => {
    setToken('abc123')
    jest.spyOn(global, 'fetch').mockResolvedValue({
        ok: true, status: 200, text: () => Promise.resolve('{"hello":"world"}'),
    })
    const data = await apiFetch('/me')
    expect(data).toEqual({ hello: 'world' })
    expect(global.fetch.mock.calls[0][1].headers.Authorization).toBe('Bearer abc123')
})

test('apiFetch clears the token on 401', async () => {
    setToken('expired')
    jest.spyOn(global, 'fetch').mockResolvedValue({
        ok: false, status: 401, text: () => Promise.resolve('{"detail":"Could not validate credentials"}'),
    })
    await expect(apiFetch('/applications')).rejects.toBeInstanceOf(ApiError)
    expect(getToken()).toBeNull()
})

test('apiFetch turns FastAPI validation errors into one message', async () => {
    jest.spyOn(global, 'fetch').mockResolvedValue({
        ok: false, status: 422,
        text: () => Promise.resolve('{"detail":[{"msg":"Field required"},{"msg":"Too long"}]}'),
    })
    await expect(apiFetch('/applications', { auth: false })).rejects.toThrow('Field required. Too long')
})

test('helpers: logoColor is stable, timeAgo treats server times as UTC', () => {
    expect(logoColor('Stripe')).toBe(logoColor('Stripe'))
    const fiveMinAgo = new Date(Date.now() - 5 * 60 * 1000).toISOString().replace('Z', '')
    expect(timeAgo(fiveMinAgo)).toBe('5m ago')
})

test('apiFetch shows a friendly message when the server returns an HTML error page', async () => {
    // Regression (review round 2): Render's "waking up" page is HTML,
    // and JSON.parse used to surface "Unexpected token '<'".
    jest.spyOn(global, 'fetch').mockResolvedValue({
        ok: false, status: 502, text: () => Promise.resolve('<html>Bad Gateway</html>'),
    })
    await expect(apiFetch('/applications')).rejects.toThrow(/starting up/)
})
