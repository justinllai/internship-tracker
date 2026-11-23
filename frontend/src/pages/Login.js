// ============================================================
// Login.js — The sign-in page
// Collects email + password, calls POST /login through api.js,
// stores the JWT, and goes to the tracker.
// Logic is the same as before; what changed:
//   - fetch() details moved into api.js (api.login)
//   - inline styles replaced by shared CSS classes
//   - <label htmlFor> wired to inputs (screen readers + clicking
//     the label focuses the field)
// ============================================================

import { useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { api, getToken, setToken } from '../api'
import AuthLayout from '../components/AuthLayout'

function Login() {
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [error, setError] = useState(null)
    const [loading, setLoading] = useState(false)
    const navigate = useNavigate()

    // Already signed in? Skip the login screen.
    if (getToken()) return <Navigate to="/dashboard" replace />

    async function handleSubmit(e) {
        e.preventDefault()          // stop the browser's full-page form reload
        setError(null)
        setLoading(true)
        try {
            const data = await api.login(email, password)
            setToken(data.access_token)
            navigate('/dashboard')
        } catch (err) {
            setError(err.message)
        } finally {
            setLoading(false)
        }
    }

    return (
        <AuthLayout
            headline={<>Track every application. <strong>Hear back faster.</strong></>}
            switchText="New here?" switchTo="/register" switchLabel="Join now">
            <form className="auth-form" onSubmit={handleSubmit}>
                {error && <div className="alert alert-error" role="alert">{error}</div>}
                <div className="field">
                    <label htmlFor="email">Email</label>
                    <input id="email" className="input" type="email" autoComplete="email" required
                        value={email} onChange={(e) => setEmail(e.target.value)} />
                </div>
                <div className="field">
                    <label htmlFor="password">Password</label>
                    <input id="password" className="input" type="password" autoComplete="current-password" required
                        value={password} onChange={(e) => setPassword(e.target.value)} />
                </div>
                <button type="submit" className="btn btn-primary btn-block" disabled={loading}>
                    {loading ? 'Signing in…' : 'Sign in'}
                </button>
            </form>
        </AuthLayout>
    )
}

export default Login
