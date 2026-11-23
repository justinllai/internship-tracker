// ============================================================
// OAuthCallback.js — Where Google sends the user back to
// URL: /oauth/gmail?code=...&state=...   (or ?error=access_denied)
//
// We immediately:
//   1. read code + state from the URL
//   2. REMOVE them from the address bar (history.replaceState) so
//      the one-time code isn't left in browser history
//   3. POST them to the backend WITH our login token — that's how
//      the backend proves the same user started and finished
//      the flow (see backend/routers/email_routes.py)
// ============================================================

import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api'
import { useSession } from '../context/SessionContext'

function OAuthCallback() {
    const navigate = useNavigate()
    const { refreshMe } = useSession()
    const [error, setError] = useState(null)
    // React 18+ StrictMode runs effects twice in development. An
    // OAuth code is single-use, so guard against sending it twice.
    const sent = useRef(false)

    useEffect(() => {
        if (sent.current) return
        sent.current = true

        const params = new URLSearchParams(window.location.search)
        const code = params.get('code')
        const state = params.get('state')
        const googleError = params.get('error')
        window.history.replaceState(null, '', window.location.pathname)

        if (googleError) {
            setError(googleError === 'access_denied'
                ? 'You chose not to connect Gmail. Nothing was shared.'
                : `Google returned an error: ${googleError}`)
            return
        }
        if (!code || !state) {
            setError('This page was opened without a Google authorization code.')
            return
        }
        api.emailOAuthComplete(code, state)
            .then(() => refreshMe())     // nav/session now knows Gmail is connected
            .then(() => navigate('/settings?gmail=connected', { replace: true }))
            .catch(err => setError(err.message))
    }, [navigate, refreshMe])

    return (
        <div className="page one-col">
            <div className="card">
                <div className="card-body stack" style={{ alignItems: 'center', textAlign: 'center', padding: 32 }}>
                    {error ? (
                        <>
                            <div className="alert alert-error">{error}</div>
                            <Link to="/settings" className="btn btn-outline">Back to settings</Link>
                        </>
                    ) : (
                        <>
                            <span className="spinner" style={{ width: 28, height: 28, color: 'var(--brand)' }} />
                            <p>Finishing your Gmail connection…</p>
                        </>
                    )}
                </div>
            </div>
        </div>
    )
}

export default OAuthCallback
