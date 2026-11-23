// ============================================================
// Tracker.js — The home page (replaces Dashboard.js)
// ------------------------------------------------------------
// Three columns, like a professional social feed:
//   LEFT   profile card + pipeline counts (click to filter)
//   CENTER "composer" to add an application + the feed of cards
//   RIGHT  inbox-tracking status + internships near you
//
// Data flow: this page owns the `applications` state and passes
// callbacks down to each ApplicationCard. Cards never fetch
// anything themselves ("lift state up").
// ============================================================

import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { STATUSES, logoColor } from '../constants'
import { useSession } from '../context/SessionContext'
import { useVisiblePolling } from '../hooks/useVisiblePolling'
import ApplicationCard from '../components/ApplicationCard'
import ApplicationForm from '../components/ApplicationForm'
import EmailConsentModal from '../components/EmailConsentModal'
import InboxCard from '../components/InboxCard'
import { BriefcaseIcon, PinIcon } from '../components/Icons'

function ProfileCard({ me, applications, filter, setFilter }) {
    const counts = useMemo(() => {
        const c = Object.fromEntries(STATUSES.map(s => [s, 0]))
        applications.forEach(a => { if (c[a.status] !== undefined) c[a.status] += 1 })
        return c
    }, [applications])

    const initial = (me?.username || '?').charAt(0).toUpperCase()
    return (
        <section className="card">
            <div className="profile-cover" />
            <div className="profile-avatar" aria-hidden="true">{initial}</div>
            <div className="profile-name">{me?.username || '…'}</div>
            <div className="profile-meta">
                {me?.location_label ? <><PinIcon /> {me.location_label}</> : <Link to="/jobs">Set your location</Link>}
            </div>
            <div className="divider" />
            <button className={`stat-row${filter === 'All' ? ' active' : ''}`} onClick={() => setFilter('All')}>
                <span>All applications</span><strong>{applications.length}</strong>
            </button>
            {STATUSES.map(s => (
                <button key={s} className={`stat-row${filter === s ? ' active' : ''}`} onClick={() => setFilter(s)}>
                    <span>{s}</span><strong>{counts[s]}</strong>
                </button>
            ))}
            <div style={{ height: 8 }} />
        </section>
    )
}

function JobsNearYou({ me }) {
    const [jobs, setJobs] = useState(null)

    useEffect(() => {
        if (!me?.location_label || !me?.jobs_configured) return
        let cancelled = false   // ignore the response if the user navigated away
        api.searchJobs({ q: 'software engineer', location: me.location_label, radius_km: 40 })
            .then(r => { if (!cancelled) setJobs(r.results.slice(0, 4)) })
            .catch(() => { if (!cancelled) setJobs([]) })
        return () => { cancelled = true }
    }, [me?.location_label, me?.jobs_configured])

    return (
        <section className="card">
            <div className="card-header"><h2 className="card-title">Internships near you</h2></div>
            <div className="card-body" style={{ paddingTop: 8 }}>
                {!me?.location_label ? (
                    <p className="muted small">Share your city to see open internships nearby. <Link to="/jobs">Set location →</Link></p>
                ) : jobs === null ? (
                    <div className="stack">{[1, 2, 3].map(i => <div key={i} className="skeleton" style={{ height: 36 }} />)}</div>
                ) : jobs.length === 0 ? (
                    <p className="muted small">No recent postings found near {me.location_label}.</p>
                ) : (
                    <div className="stack" style={{ gap: 10 }}>
                        {jobs.map(j => (
                            <div key={j.external_id} className="row" style={{ flexWrap: 'nowrap', alignItems: 'flex-start' }}>
                                <div className="company-logo" style={{ width: 32, height: 32, fontSize: 14, background: logoColor(j.company) }}>
                                    {j.company.charAt(0)}
                                </div>
                                <div style={{ minWidth: 0 }}>
                                    <div className="bold small truncate">{j.title}</div>
                                    <div className="muted small truncate">{j.company} · {j.location}</div>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
            <div className="card-footer"><Link to="/jobs" className="bold small">Show all →</Link></div>
        </section>
    )
}

function Tracker() {
    const { me, refreshUnread } = useSession()
    const [applications, setApplications] = useState([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)
    const [filter, setFilter] = useState('All')
    const [editing, setEditing] = useState(null)         // null | {} (new) | application
    const [consentFor, setConsentFor] = useState(null)   // application to ask about email tracking

    const gmail = me?.gmail
    const gmailActive = Boolean(gmail?.connected && gmail?.status === 'active')

    const load = useCallback(async () => {
        try {
            setApplications(await api.listApplications())
            setError(null)
        } catch (err) {
            setError(err.message)
        } finally {
            setLoading(false)
        }
    }, [])

    useEffect(() => { load() }, [load])
    // Refresh the feed every 60s too, so newly detected emails appear
    // on cards without a reload.
    useVisiblePolling(load, 60000, !loading)

    // Replace one application in the list (after an update)
    const replace = (updated) =>
        setApplications(list => list.map(a => (a.id === updated.id ? updated : a)))

    async function handleStatusChange(app, status) {
        try {
            const updated = await api.updateApplication(app.id, { status })
            replace(updated)
            // Just-in-time consent: they just APPLIED → offer tracking
            if (app.status === 'Saved' && status !== 'Saved' && !updated.track_email) setConsentFor(updated)
        } catch (err) {
            setError(err.message)
        }
    }

    async function handleDelete(app) {
        if (!window.confirm(`Delete your ${app.position} application at ${app.company_name}?`)) return
        try {
            await api.deleteApplication(app.id)
            setApplications(list => list.filter(a => a.id !== app.id))
            refreshUnread()
        } catch (err) {
            setError(err.message)
        }
    }

    async function handleUntrack(app) {
        try {
            replace(await api.updateApplication(app.id, { track_email: false }))
        } catch (err) {
            setError(err.message)
        }
    }

    function handleSaved(saved, { created }) {
        setEditing(null)
        if (created) {
            setApplications(list => [saved, ...list])
            if (saved.status !== 'Saved') setConsentFor(saved)    // ask right after applying
        } else {
            replace(saved)
        }
    }

    const visible = filter === 'All' ? applications : applications.filter(a => a.status === filter)

    return (
        <div className="page">
            {/* LEFT */}
            <aside className="column sticky-col">
                <ProfileCard me={me} applications={applications} filter={filter} setFilter={setFilter} />
            </aside>

            {/* CENTER */}
            <section className="column">
                <div className="card">
                    <div className="composer">
                        <div className="profile-avatar" style={{ width: 48, height: 48, margin: 0, fontSize: 20, border: 'none' }} aria-hidden="true">
                            {(me?.username || '?').charAt(0).toUpperCase()}
                        </div>
                        <button className="composer-trigger" onClick={() => setEditing({})}>Add an application you've sent…</button>
                    </div>
                    <div className="card-footer row" style={{ justifyContent: 'space-around' }}>
                        <button className="btn btn-ghost btn-sm" onClick={() => setEditing({ status: 'Saved' })}>+ Save for later</button>
                        <Link className="btn btn-ghost btn-sm" to="/jobs"><BriefcaseIcon size={16} /> Find internships</Link>
                    </div>
                </div>

                {error && <div className="alert alert-error" role="alert">{error}</div>}

                {gmail?.status === 'needs_reauth' && (
                    <div className="alert alert-error">
                        Gmail access expired, so replies aren't being tracked. <Link to="/settings" className="bold">Reconnect →</Link>
                    </div>
                )}

                <div className="card">
                    <div className="card-header">
                        <h2 className="card-title">{filter === 'All' ? 'Your applications' : `${filter} applications`}</h2>
                        <span className="muted small">{visible.length} shown</span>
                    </div>
                    <div className="card-body" style={{ paddingBottom: 8 }}>
                        <div className="chip-row" role="group" aria-label="Filter by status">
                            {['All', ...STATUSES].map(s => (
                                <button key={s} className={`chip${filter === s ? ' active' : ''}`} aria-pressed={filter === s}
                                    onClick={() => setFilter(s)}>{s}</button>
                            ))}
                        </div>
                    </div>

                    {loading ? (
                        <div className="feed-item"><div className="skeleton" style={{ height: 80, flex: 1 }} /></div>
                    ) : visible.length === 0 ? (
                        <div className="empty">
                            <h3>{applications.length === 0 ? 'No applications yet' : `Nothing in "${filter}"`}</h3>
                            <p>{applications.length === 0
                                ? 'Add one you already sent, or find internships near you.'
                                : 'Try another filter.'}</p>
                            {applications.length === 0 && (
                                <div className="row mt-16" style={{ justifyContent: 'center' }}>
                                    <button className="btn btn-primary" onClick={() => setEditing({})}>Add application</button>
                                    <Link className="btn btn-outline" to="/jobs">Find internships</Link>
                                </div>
                            )}
                        </div>
                    ) : (
                        visible.map(app => (
                            <ApplicationCard key={app.id} app={app} gmailConnected={gmailActive}
                                onStatusChange={handleStatusChange} onEdit={setEditing} onDelete={handleDelete}
                                onTrack={setConsentFor} onUntrack={handleUntrack} />
                        ))
                    )}
                </div>
            </section>

            {/* RIGHT */}
            <aside className="column right-rail sticky-col">
                <InboxCard onSynced={load} />
                <JobsNearYou me={me} />
            </aside>

            {editing && <ApplicationForm initial={editing} onClose={() => setEditing(null)} onSaved={handleSaved} />}
            {consentFor && (
                <EmailConsentModal application={consentFor} gmail={gmail}
                    onClose={() => setConsentFor(null)} onTracked={replace} />
            )}
        </div>
    )
}

export default Tracker
