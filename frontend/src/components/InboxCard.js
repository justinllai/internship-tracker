// ============================================================
// InboxCard.js — Gmail tracking status (right rail + Settings)
// Shows one of four states: not configured on server, not
// connected, needs reconnect (7-day expiry), or connected —
// with a "Check now" button that triggers an immediate sync.
// ============================================================

import { useState } from 'react'
import { api } from '../api'
import { timeAgo } from '../constants'
import { useSession } from '../context/SessionContext'
import { MailIcon, RefreshIcon } from './Icons'

function InboxCard({ onSynced }) {
    const { me, refreshMe, refreshUnread } = useSession()
    const [busy, setBusy] = useState(false)
    const [message, setMessage] = useState(null)
    const gmail = me?.gmail

    async function connect() {
        setBusy(true)
        try {
            const { auth_url } = await api.emailConnectUrl()
            window.location.assign(auth_url)
        } catch (err) {
            setMessage(err.message)
            setBusy(false)
        }
    }

    async function checkNow() {
        setBusy(true)
        setMessage(null)
        try {
            const r = await api.emailSync()
            if (r.skipped === 'already_running') setMessage('A check is already running — results will appear shortly.')
            else if (r.skipped === 'needs_reauth') setMessage('Gmail needs to be reconnected.')
            else if (r.skipped === 'google_unavailable') setMessage("Couldn't reach Gmail — see the error above. We'll retry in about 15 minutes.")
            else if (r.skipped === 'backing_off') setMessage('The last check failed, so we are pausing ~15 minutes before retrying.')
            else setMessage(r.new_events ? `${r.new_events} new update${r.new_events > 1 ? 's' : ''} found!` : 'No new replies yet.')
            await Promise.all([refreshMe(), refreshUnread()])
            onSynced?.()
        } catch (err) {
            setMessage(err.message)
        } finally {
            setBusy(false)
        }
    }

    let body
    if (!gmail) {
        body = <div className="skeleton" style={{ height: 40 }} />
    } else if (!gmail.configured) {
        body = <p className="muted small">Inbox tracking isn't set up on this server yet.</p>
    } else if (!gmail.connected) {
        body = (
            <>
                <p className="muted small">Get notified the moment a company replies. Read-only, and only for applications you choose.</p>
                <button className="btn btn-outline btn-sm mt-8" onClick={connect} disabled={busy}><MailIcon /> Connect Gmail</button>
            </>
        )
    } else if (gmail.status === 'needs_reauth') {
        body = (
            <>
                <div className="alert alert-error small">Google ended access (happens every 7 days in testing mode).</div>
                <button className="btn btn-primary btn-sm mt-8" onClick={connect} disabled={busy}>Reconnect Gmail</button>
            </>
        )
    } else {
        body = (
            <>
                <p className="small"><span style={{ color: 'var(--success)' }}>●</span> Connected as <strong>{gmail.email_address || 'Gmail'}</strong></p>
                <p className="muted small">Last checked {gmail.last_synced_at ? timeAgo(gmail.last_synced_at) : 'never'}</p>
                {/* Never fail silently: if the last sync errored, say so */}
                {gmail.last_error && (
                    <div className="alert alert-error small mt-8">Last check failed: {gmail.last_error}</div>
                )}
                <button className="btn btn-outline btn-sm mt-8" onClick={checkNow} disabled={busy}>
                    {busy ? <span className="spinner" /> : <RefreshIcon />} Check now
                </button>
            </>
        )
    }

    return (
        <section className="card">
            <div className="card-header"><h2 className="card-title">Inbox tracking</h2></div>
            <div className="card-body">
                {body}
                {message && <p className="small mt-8" role="status">{message}</p>}
            </div>
        </section>
    )
}

export default InboxCard
