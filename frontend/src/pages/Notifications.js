// ============================================================
// Notifications.js — Company replies detected in your inbox
// ------------------------------------------------------------
// Each email update shows who wrote, the subject, whether you've
// opened it in Gmail yet, and — if our classifier thinks the
// status changed — a suggestion you can apply with one click.
// We SUGGEST instead of auto-changing because keyword rules can
// misread emails; a wrong "Rejected" is worse than one click.
// ============================================================

import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { timeAgo } from '../constants'
import { useSession } from '../context/SessionContext'
import { useVisiblePolling } from '../hooks/useVisiblePolling'
import InboxCard from '../components/InboxCard'
import StatusBadge from '../components/StatusBadge'
import { BellIcon, MailIcon } from '../components/Icons'

const ICON_STYLE = {
    offer: { background: 'var(--offer-bg)', color: 'var(--offer)' },
    interview: { background: 'var(--interview-bg)', color: 'var(--interview)' },
    rejection: { background: 'var(--rejected-bg)', color: 'var(--rejected)' },
}

function NotificationItem({ n, onApply, onDismiss, onRead }) {
    const style = ICON_STYLE[n.email?.classification] || { background: 'var(--brand-soft)', color: 'var(--brand)' }
    const showSuggestion = n.suggested_status && !n.suggestion_resolved

    return (
        // Clicking anywhere on an unread item marks it read (works for
        // mouse, touch, and — via the buttons inside — keyboard users)
        <article className={`notif${n.is_read ? '' : ' unread'}`} onClick={() => !n.is_read && onRead(n)}>
            <span className="notif-icon" style={style}>{n.kind === 'reauth_needed' ? <BellIcon size={20} /> : <MailIcon />}</span>
            <div className="notif-body">
                <div className="row-between">
                    <span className="notif-title">{n.title}</span>
                    <span className="muted small">{timeAgo(n.created_at)}</span>
                </div>
                {n.body && <div className="notif-text">“{n.body}”</div>}
                {n.email && (
                    <div className="notif-text">
                        From {n.email.from_name ? `${n.email.from_name} <${n.email.from_address}>` : n.email.from_address}
                        {n.email.ambiguous && ' · matched to your most recent application at this company'}
                    </div>
                )}
                {n.email?.is_unread && (
                    <span className="pill-warning"><MailIcon /> You haven't opened this in Gmail yet</span>
                )}

                {showSuggestion && (
                    <div className="row mt-8">
                        <span className="small muted">Update status:</span>
                        {n.application_status && <StatusBadge status={n.application_status} />}
                        <span className="muted">→</span>
                        <StatusBadge status={n.suggested_status} />
                        <button className="btn btn-primary btn-sm" onClick={() => onApply(n)}>Apply</button>
                        <button className="btn btn-ghost btn-sm" onClick={() => onDismiss(n)}>Dismiss</button>
                    </div>
                )}
                {n.kind === 'reauth_needed' && (
                    <Link to="/settings" className="btn btn-outline btn-sm mt-8">Reconnect Gmail</Link>
                )}
            </div>
        </article>
    )
}

function Notifications() {
    const { refreshUnread } = useSession()
    const [items, setItems] = useState(null)
    const [error, setError] = useState(null)

    const load = useCallback(async () => {
        try {
            setItems(await api.notifications())
        } catch (err) {
            setError(err.message)
        }
    }, [])

    useEffect(() => { load() }, [load])
    useVisiblePolling(load, 30000, items !== null)

    const patch = (id, changes) => setItems(list => list.map(n => (n.id === id ? { ...n, ...changes } : n)))

    async function handleRead(n) {
        patch(n.id, { is_read: true })        // optimistic: update UI first
        try {
            await api.markRead(n.id)
            refreshUnread()
        } catch { /* next poll will correct it */ }
    }

    async function handleApply(n) {
        try {
            const app = await api.applySuggestion(n.id)
            patch(n.id, { suggestion_resolved: true, is_read: true, application_status: app.status })
            refreshUnread()
        } catch (err) {
            setError(err.message)
            load()
        }
    }

    async function handleDismiss(n) {
        try {
            patch(n.id, await api.dismissSuggestion(n.id))
            refreshUnread()
        } catch (err) {
            setError(err.message)
        }
    }

    async function handleReadAll() {
        await api.markAllRead()
        setItems(list => list.map(n => ({ ...n, is_read: true })))
        refreshUnread()
    }

    return (
        <div className="page two-col">
            <section className="column">
                <div className="card">
                    <div className="card-header">
                        <h1 className="card-title" style={{ fontSize: 20 }}>Updates</h1>
                        {items?.some(n => !n.is_read) && (
                            <button className="btn btn-ghost btn-sm" onClick={handleReadAll}>Mark all as read</button>
                        )}
                    </div>
                    <div className="card-body muted small" style={{ paddingTop: 4 }}>
                        Replies from companies you're tracking appear here automatically.
                    </div>
                    {error && <div className="card-body"><div className="alert alert-error">{error}</div></div>}
                    {items === null ? (
                        <div className="card-body"><div className="skeleton" style={{ height: 64 }} /></div>
                    ) : items.length === 0 ? (
                        <div className="empty">
                            <h3>No updates yet</h3>
                            <p>Turn on "Notify me when they reply" for an application, and replies will show up here.</p>
                        </div>
                    ) : (
                        items.map(n => (
                            <NotificationItem key={n.id} n={n} onApply={handleApply} onDismiss={handleDismiss} onRead={handleRead} />
                        ))
                    )}
                </div>
            </section>
            <aside className="column right-rail sticky-col">
                <InboxCard onSynced={load} />
            </aside>
        </div>
    )
}

export default Notifications
