// ============================================================
// EmailConsentModal.js — "Just-in-time" consent for email
// ------------------------------------------------------------
// We never ask for inbox access at signup. We ask at the moment
// it's useful — right after you apply — and we say exactly what
// we'll look at: replies from THIS company, since THIS date.
// Privacy engineers call this just-in-time consent; it's more
// honest than a blanket "give us your inbox" and people are far
// more likely to say yes when the value is obvious.
//
// Two cases:
//   - Gmail already connected → one click turns tracking on for
//     this application.
//   - Not connected → we turn tracking on for this app, then send
//     the user to Google's consent screen. When Google sends them
//     back, this application is already marked to be tracked.
// ============================================================

import { useState } from 'react'
import { api } from '../api'
import Modal from './Modal'
import { MailIcon, ShieldIcon } from './Icons'

function EmailConsentModal({ application, gmail, onClose, onTracked }) {
    const [domain, setDomain] = useState(application.company_domain || '')
    const [busy, setBusy] = useState(false)
    const [error, setError] = useState(null)

    const connected = gmail?.connected
    const configured = gmail?.configured !== false

    async function handleTrack() {
        setBusy(true)
        setError(null)
        try {
            const updated = await api.updateApplication(application.id, {
                track_email: true,
                company_domain: domain.trim() || null,
            })
            if (connected) {
                onTracked(updated)
                onClose()
                return
            }
            // Not connected yet: get Google's consent URL and go there.
            const { auth_url } = await api.emailConnectUrl()
            window.location.assign(auth_url)
        } catch (err) {
            setError(err.message)
            setBusy(false)
        }
    }

    return (
        <Modal title={`Get notified when ${application.company_name} replies?`} onClose={onClose}
            footer={<>
                <button className="btn btn-ghost" onClick={onClose}>Not now</button>
                <button className="btn btn-primary" onClick={handleTrack} disabled={busy || !configured}>
                    {busy ? 'Working…' : connected ? 'Track replies' : 'Connect Gmail & track'}
                </button>
            </>}>
            <div className="row" style={{ flexWrap: 'nowrap', alignItems: 'flex-start' }}>
                <span className="notif-icon" style={{ background: 'var(--brand-soft)', color: 'var(--brand)' }}><MailIcon /></span>
                <div>
                    We'll check your inbox for replies from <strong>{application.company_name}</strong>, notify you,
                    and suggest a status update (like "Interview") that you can apply with one click.
                </div>
            </div>

            <div className="field">
                <label htmlFor="consent-domain">Company email domain (optional, improves accuracy)</label>
                <input id="consent-domain" className="input" placeholder="e.g. stripe.com"
                    value={domain} onChange={(e) => setDomain(e.target.value)} />
                <span className="hint">We also recognize common hiring platforms (Greenhouse, Lever, Workday…) when they mention {application.company_name}.</span>
            </div>

            <div className="alert alert-info" style={{ alignItems: 'flex-start' }}>
                <ShieldIcon size={20} />
                <ul style={{ margin: 0, paddingLeft: 16 }}>
                    <li>Read-only access. We can't send, delete, or change anything.</li>
                    <li>We only search for messages since you applied from this company or the hiring platforms
                        companies use (Greenhouse, Lever…). Messages that aren't about your tracked applications are ignored and never stored.</li>
                    <li>We keep the sender, subject and date — never the email body.</li>
                    <li>Disconnect anytime in Settings; we delete what we stored and revoke access with Google.</li>
                </ul>
            </div>

            {!configured && (
                <div className="alert alert-error">Email tracking isn't set up on this server yet (missing Google OAuth credentials).</div>
            )}
            {error && <div className="alert alert-error" role="alert">{error}</div>}
        </Modal>
    )
}

export default EmailConsentModal
