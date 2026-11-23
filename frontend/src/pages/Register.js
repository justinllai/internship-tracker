// ============================================================
// Register.js — Create an account
// After a successful register we log the user straight in
// (one less step) by calling /login with the same credentials.
// ============================================================

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, setToken } from '../api'
import AuthLayout from '../components/AuthLayout'

function Register() {
    const [email, setEmail] = useState('')
    const [username, setUsername] = useState('')
    const [password, setPassword] = useState('')
    const [error, setError] = useState(null)
    const [loading, setLoading] = useState(false)
    const navigate = useNavigate()

    async function handleSubmit(e) {
        e.preventDefault()
        setError(null)
        setLoading(true)
        try {
            await api.register(email, username, password)
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
            headline={<>Your internship search, <strong>organized.</strong></>}
            switchText="Already have an account?" switchTo="/" switchLabel="Sign in">
            <form className="auth-form" onSubmit={handleSubmit}>
                {error && <div className="alert alert-error" role="alert">{error}</div>}
                <div className="field">
                    <label htmlFor="email">Email</label>
                    <input id="email" className="input" type="email" autoComplete="email" required
                        value={email} onChange={(e) => setEmail(e.target.value)} />
                </div>
                <div className="field">
                    <label htmlFor="username">Username</label>
                    <input id="username" className="input" autoComplete="username" required minLength={3} maxLength={30}
                        value={username} onChange={(e) => setUsername(e.target.value)} />
                </div>
                <div className="field">
                    <label htmlFor="password">Password (8+ characters)</label>
                    <input id="password" className="input" type="password" autoComplete="new-password" required minLength={8}
                        value={password} onChange={(e) => setPassword(e.target.value)} />
                </div>
                <button type="submit" className="btn btn-primary btn-block" disabled={loading}>
                    {loading ? 'Creating account…' : 'Agree & join'}
                </button>
            </form>
        </AuthLayout>
    )
}

export default Register
