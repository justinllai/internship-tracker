// ============================================================
// ApplicationCard.js — One application in the feed
// Shows: company "logo", role, status, a pipeline progress bar,
// whether we're watching the inbox for it, and the timeline of
// company emails we detected.
// It doesn't call the API itself — it calls the callbacks the
// parent passes in (onStatusChange, onEdit...). Keeping data
// logic in the page and display logic in the card is the
// "container vs presentational component" split.
// ============================================================

import { PIPELINE, STATUSES, logoColor, timeAgo } from '../constants'
import StatusBadge from './StatusBadge'
import { EditIcon, ExternalIcon, MailIcon, PinIcon, TrashIcon } from './Icons'

const CLASSIFICATION_LABEL = {
    offer: 'Offer',
    interview: 'Interview request',
    rejection: 'Rejection',
    acknowledgment: 'Application received',
    other: 'Message',
}

function Pipeline({ status }) {
    // Rejected: show how far they got before the rejection (gray-red)
    const reached = status === 'Rejected' ? 'Applied' : status
    const index = PIPELINE.indexOf(reached)
    return (
        <div className={`pipeline ${status.toLowerCase()}`} aria-hidden="true">
            {PIPELINE.map((step, i) => (
                <div key={step} className={`pipeline-step${i <= index ? ' done' : ''}`} title={step} />
            ))}
        </div>
    )
}

function ApplicationCard({ app, gmailConnected, onStatusChange, onEdit, onDelete, onTrack, onUntrack }) {
    const emails = app.email_events || []
    const canTrack = app.status !== 'Saved'

    return (
        <article className="feed-item">
            <div className="company-logo" style={{ background: logoColor(app.company_name) }} aria-hidden="true">
                {app.company_name.charAt(0).toUpperCase()}
            </div>

            <div className="feed-main">
                <div className="row-between" style={{ alignItems: 'flex-start' }}>
                    <div style={{ minWidth: 0 }}>
                        <h3 className="feed-title">
                            {app.job_url
                                ? <a href={app.job_url} target="_blank" rel="noopener noreferrer">{app.position} <ExternalIcon /></a>
                                : app.position}
                        </h3>
                        <div className="feed-sub">{app.company_name}</div>
                        <div className="feed-meta">
                            {app.location && <span className="tag"><PinIcon /> {app.location}</span>}
                            <span>{app.status === 'Saved' ? 'Saved' : 'Applied'} {timeAgo(app.date_applied)}</span>
                            {app.source && app.source !== 'manual' && <span>via {app.source}</span>}
                        </div>
                    </div>
                    <StatusBadge status={app.status} />
                </div>

                <Pipeline status={app.status} />

                {app.notes && <p className="feed-notes">{app.notes}</p>}

                {/* Inbox tracking indicator */}
                {canTrack && (
                    <div className="row mt-8 small">
                        {app.track_email ? (
                            <>
                                <span className="tag" style={{ color: gmailConnected ? 'var(--success)' : 'var(--interview)' }}>
                                    <MailIcon /> {gmailConnected ? 'Watching inbox for replies' : 'Tracking paused — Gmail not connected'}
                                </span>
                                <button className="btn btn-ghost btn-sm" onClick={() => onUntrack(app)}>Stop</button>
                            </>
                        ) : (
                            <button className="btn btn-ghost btn-sm" style={{ paddingLeft: 0 }} onClick={() => onTrack(app)}>
                                <MailIcon /> Notify me when they reply
                            </button>
                        )}
                    </div>
                )}

                {/* Timeline of detected company emails (newest first) */}
                {emails.length > 0 && (
                    <div className="timeline">
                        {emails.slice(0, 3).map(ev => (
                            <div key={ev.id} className="timeline-item">
                                <div><strong>{CLASSIFICATION_LABEL[ev.classification] || 'Message'}</strong> · <span className="muted">{ev.subject}</span></div>
                                <div className="when">
                                    {ev.from_address} · {timeAgo(ev.received_at)}
                                    {ev.is_unread && <span className="pill-warning" style={{ marginLeft: 6, marginTop: 0 }}>Unopened in Gmail</span>}
                                </div>
                            </div>
                        ))}
                    </div>
                )}

                <div className="feed-actions">
                    <label htmlFor={`status-${app.id}`} className="sr-only">Change status</label>
                    <select id={`status-${app.id}`} className="select" style={{ width: 'auto', minHeight: 30 }}
                        value={app.status} onChange={(e) => onStatusChange(app, e.target.value)}>
                        {STATUSES.map(s => <option key={s}>{s}</option>)}
                    </select>
                    <button className="btn btn-ghost btn-sm" onClick={() => onEdit(app)}><EditIcon /> Edit</button>
                    <button className="btn btn-danger btn-sm" onClick={() => onDelete(app)}><TrashIcon /> Delete</button>
                </div>
            </div>
        </article>
    )
}

export default ApplicationCard
