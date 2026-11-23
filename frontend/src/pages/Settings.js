// ============================================================
// Settings.js — Connected accounts, location, and privacy
// Users should always be able to SEE and UNDO every permission
// they gave us. This page is where that happens.
// ============================================================

import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api } from '../api'
import { useSession } from '../context/SessionContext'
import InboxCard from '../components/InboxCard'
import LocationPicker from '../components/LocationPicker'
import { ShieldIcon } from '../components/Icons'

function Settings() {
    const { me, refreshMe, refreshUnread } = useSession()
    const [params] = useSearchParams()
    const [message, setMessage] = useState(params.get('gmail') === 'connected' ? 'Gmail connected! Tracked applications will now be checked for replies.' : null)
    const [error, setError] = useState(null)
    const [confirmDisconnect, setConfirmDisconnect] = useState(false)

    async function saveLocation(label) {
        setError(null)
        try {
            await api.saveLocation(label)
            await refreshMe()
            setMessage(label ? `Default location set to ${label}.` : 'Saved location removed.')
        } catch (err) {
            setError(err.message)
        }
    }

    async function disconnect() {
        setError(null)
        try {
            await api.emailDisconnect()
            await Promise.all([refreshMe(), refreshUnread()])
            setConfirmDisconnect(false)
            setMessage('Gmail disconnected. Access was revoked with Google and all email-derived data was deleted.')
        } catch (err) {
            setError(err.message)
        }
    }

    return (
        <div className="page one-col">
            <section className="column">
                <h1 style={{ fontSize: 24, fontWeight: 600, margin: '0 0 8px' }}>Settings & privacy</h1>
                {message && <div className="alert alert-success" role="status">{message}</div>}
                {error && <div className="alert alert-error" role="alert">{error}</div>}

                <InboxCard />

                {me?.gmail?.connected && (
                    <section className="card">
                        <div className="card-body stack">
                            <h2 className="card-title">Disconnect Gmail</h2>
                            <p className="muted small">
                                Revokes our read-only access with Google and permanently deletes every email update we stored.
                                Your applications stay.
                            </p>
                            {!confirmDisconnect ? (
                                <button className="btn btn-danger" style={{ alignSelf: 'flex-start', border: '1px solid var(--danger)' }}
                                    onClick={() => setConfirmDisconnect(true)}>Disconnect Gmail</button>
                            ) : (
                                <div className="row">
                                    <span className="small bold">Are you sure?</span>
                                    <button className="btn btn-danger btn-sm" style={{ border: '1px solid var(--danger)' }} onClick={disconnect}>Yes, disconnect</button>
                                    <button className="btn btn-ghost btn-sm" onClick={() => setConfirmDisconnect(false)}>Cancel</button>
                                </div>
                            )}
                        </div>
                    </section>
                )}

                <section className="card">
                    <div className="card-body stack">
                        <h2 className="card-title">Default job-search location</h2>
                        <p className="muted small">Currently: <strong>{me?.location_label || 'not set'}</strong></p>
                        <LocationPicker value={null} onChange={saveLocation} />
                        {me?.location_label && (
                            <button className="btn btn-ghost btn-sm" style={{ alignSelf: 'flex-start' }} onClick={() => saveLocation(null)}>
                                Remove saved location
                            </button>
                        )}
                    </div>
                </section>

                <section className="card">
                    <div className="card-body stack small">
                        <h2 className="card-title">What we store</h2>
                        {[
                            ['Location', 'Only a city name like "San Jose, CA" — never coordinates or a street address.'],
                            ['Gmail', 'An encrypted, read-only access token. Revocable here or at myaccount.google.com/permissions.'],
                            ['Emails', 'For tracked applications only: sender, subject, date, and our label. Never the message body.'],
                            ['Search scope', 'We only search for messages from companies you marked "notify me" (or the hiring platforms they use), since you applied. Anything unrelated is ignored and never stored.'],
                        ].map(([title, text]) => (
                            <div key={title} className="row" style={{ flexWrap: 'nowrap', alignItems: 'flex-start' }}>
                                <ShieldIcon size={18} />
                                <span><strong>{title}:</strong> {text}</span>
                            </div>
                        ))}
                    </div>
                </section>
            </section>
        </div>
    )
}

export default Settings
