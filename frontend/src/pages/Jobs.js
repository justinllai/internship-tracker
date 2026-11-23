// ============================================================
// Jobs.js — Find internships near you
// ------------------------------------------------------------
// 1. Pick a location (device location or typed — LocationPicker)
// 2. Pick keywords + radius
// 3. Backend searches Adzuna and returns internship postings
// 4. "Save" → tracker as Saved.  "Apply" → opens the posting and
//    tracks it as Applied, then asks about email tracking.
// ============================================================

import { useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api } from '../api'
import { logoColor, timeAgo } from '../constants'
import { useSession } from '../context/SessionContext'
import LocationPicker from '../components/LocationPicker'
import EmailConsentModal from '../components/EmailConsentModal'
import { ExternalIcon, PinIcon, SearchIcon, ShieldIcon } from '../components/Icons'

const RADII = [10, 25, 40, 80]   // km (Adzuna's unit)

function JobCard({ job, onSave, onApply, busy }) {
    return (
        <article className="feed-item">
            <div className="company-logo" style={{ background: logoColor(job.company) }} aria-hidden="true">
                {job.company.charAt(0).toUpperCase()}
            </div>
            <div className="feed-main">
                <h3 className="feed-title">{job.title}</h3>
                <div className="feed-sub">{job.company}</div>
                <div className="feed-meta">
                    <span className="tag"><PinIcon /> {job.location}</span>
                    {job.posted_at && <span>Posted {timeAgo(job.posted_at)}</span>}
                    {job.salary && <span>{job.salary}</span>}
                </div>
                {job.description && <p className="feed-notes">{job.description}…</p>}
                <div className="feed-actions">
                    {job.already_tracked ? (
                        <span className="status status-offer">✓ In your tracker</span>
                    ) : (
                        <>
                            <button className="btn btn-primary btn-sm" onClick={() => onApply(job)} disabled={busy}>
                                Apply <ExternalIcon />
                            </button>
                            <button className="btn btn-outline btn-sm" onClick={() => onSave(job)} disabled={busy}>Save</button>
                        </>
                    )}
                </div>
            </div>
        </article>
    )
}

function Jobs() {
    const { me, refreshMe } = useSession()
    const [params] = useSearchParams()
    const [query, setQuery] = useState(params.get('q') || 'software engineer')
    const [location, setLocation] = useState('')
    const [radius, setRadius] = useState(40)
    const [results, setResults] = useState(null)
    const [searching, setSearching] = useState(false)
    const [error, setError] = useState(null)
    const [busyId, setBusyId] = useState(null)
    const [consentFor, setConsentFor] = useState(null)
    const [savedMsg, setSavedMsg] = useState(null)

    // Start from the user's saved city once /me has loaded
    useEffect(() => {
        if (me?.location_label && !location) setLocation(me.location_label)
    }, [me?.location_label]) // eslint-disable-line react-hooks/exhaustive-deps

    // A ref always holds the LATEST keywords, so effects can read them
    // without listing `query` as a dependency (which would search on
    // every keystroke).
    const queryRef = useRef(query)
    queryRef.current = query

    // Each search gets an id; only the newest one may update the page.
    // Otherwise a slow old response could overwrite a newer one
    // (a classic "race condition" in UIs).
    const latestSearch = useRef(0)

    async function runSearch(loc = location, q = query) {
        if (!loc) {
            setError('Choose a location first.')
            return
        }
        const id = ++latestSearch.current
        setSearching(true)
        setError(null)
        try {
            const r = await api.searchJobs({ q, location: loc, radius_km: radius })
            if (id === latestSearch.current) setResults(r.results)
        } catch (err) {
            if (id === latestSearch.current) {
                setError(err.message)
                setResults(null)
            }
        } finally {
            if (id === latestSearch.current) setSearching(false)
        }
    }

    // Effect 1: ?q= in the URL changed (nav-bar search) → use those keywords
    useEffect(() => {
        const q = params.get('q')
        if (!q) return
        setQuery(q)
        if (location) runSearch(location, q)
    }, [params]) // eslint-disable-line react-hooks/exhaustive-deps

    // Effect 2: location changed → search with whatever keywords are typed now
    useEffect(() => {
        if (location) runSearch(location, queryRef.current)
    }, [location]) // eslint-disable-line react-hooks/exhaustive-deps

    async function saveDefault() {
        try {
            await api.saveLocation(location)
            await refreshMe()
            setSavedMsg('Saved as your default location.')
        } catch (err) {
            setError(err.message)
        }
    }

    function toApplication(job, status) {
        return {
            company_name: job.company, position: job.title, status, location: job.location,
            job_url: job.url, source: job.source, external_id: job.external_id,
        }
    }

    function markTracked(job) {
        setResults(list => list.map(j => (j.external_id === job.external_id ? { ...j, already_tracked: true } : j)))
    }

    async function handleSave(job) {
        setBusyId(job.external_id)
        try {
            await api.createApplication(toApplication(job, 'Saved'))
            markTracked(job)
        } catch (err) {
            if (err.status === 409) markTracked(job)
            else setError(err.message)
        } finally {
            setBusyId(null)
        }
    }

    async function handleApply(job) {
        // Open the tab FIRST, synchronously in the click handler.
        // Browsers block pop-ups that open after an `await`.
        window.open(job.url, '_blank', 'noopener,noreferrer')
        setBusyId(job.external_id)
        try {
            const created = await api.createApplication(toApplication(job, 'Applied'))
            markTracked(job)
            setConsentFor(created)       // just-in-time email consent
        } catch (err) {
            if (err.status === 409) markTracked(job)
            else setError(err.message)
        } finally {
            setBusyId(null)
        }
    }

    return (
        <div className="page two-col">
            <section className="column">
                <div className="card">
                    <div className="card-header"><h1 className="card-title" style={{ fontSize: 20 }}>Find internships near you</h1></div>
                    <form className="card-body stack" onSubmit={(e) => { e.preventDefault(); runSearch() }}>
                        <div className="form-grid">
                            <div className="field">
                                <label htmlFor="job-q">Role or keywords</label>
                                <input id="job-q" className="input" value={query} onChange={(e) => setQuery(e.target.value)} maxLength={100} />
                            </div>
                            <div className="field">
                                <label htmlFor="job-radius">Distance</label>
                                <select id="job-radius" className="select" value={radius} onChange={(e) => setRadius(Number(e.target.value))}>
                                    {RADII.map(r => <option key={r} value={r}>Within {r} km (~{Math.round(r * 0.621)} mi)</option>)}
                                </select>
                            </div>
                        </div>
                        <button type="submit" className="btn btn-primary" disabled={searching || !location} style={{ alignSelf: 'flex-start' }}>
                            {searching ? <span className="spinner" /> : <SearchIcon />} Search
                        </button>
                    </form>
                    <div className="card-footer">
                        <LocationPicker value={location} onChange={(label) => { setLocation(label); setSavedMsg(null) }} />
                        {location && location !== me?.location_label && (
                            <button className="btn btn-ghost btn-sm mt-8" onClick={saveDefault}>Save "{location}" as my default</button>
                        )}
                        {savedMsg && <p className="small mt-8" style={{ color: 'var(--success)' }}>{savedMsg}</p>}
                    </div>
                </div>

                {error && <div className="alert alert-error" role="alert">{error}</div>}

                {results !== null && (
                    <div className="card">
                        <div className="card-header">
                            <h2 className="card-title">{results.length} internship{results.length === 1 ? '' : 's'} near {location}</h2>
                            {/* Attribution required by Adzuna's API terms */}
                            <a href="https://www.adzuna.com" target="_blank" rel="noopener noreferrer" className="small muted">Jobs by Adzuna</a>
                        </div>
                        {results.length === 0 ? (
                            <div className="empty">
                                <h3>No internships found</h3>
                                <p>Try broader keywords (e.g. "engineer") or a larger distance.</p>
                            </div>
                        ) : (
                            <div className="mt-8">
                                {results.map(job => (
                                    <JobCard key={job.external_id} job={job} busy={busyId === job.external_id}
                                        onSave={handleSave} onApply={handleApply} />
                                ))}
                            </div>
                        )}
                    </div>
                )}
            </section>

            <aside className="column right-rail sticky-col">
                <section className="card">
                    <div className="card-header"><h2 className="card-title">How your location is used</h2></div>
                    <div className="card-body stack small">
                        <div className="row" style={{ flexWrap: 'nowrap', alignItems: 'flex-start' }}>
                            <ShieldIcon size={18} />
                            <span>Device location is rounded to about 1 km before it leaves your browser.</span>
                        </div>
                        <div className="row" style={{ flexWrap: 'nowrap', alignItems: 'flex-start' }}>
                            <ShieldIcon size={18} />
                            <span>Typed addresses are converted to a city and then discarded.</span>
                        </div>
                        <div className="row" style={{ flexWrap: 'nowrap', alignItems: 'flex-start' }}>
                            <ShieldIcon size={18} />
                            <span>Only a city name is saved — and only if you click "Save as my default".</span>
                        </div>
                    </div>
                </section>
            </aside>

            {consentFor && (
                <EmailConsentModal application={consentFor} gmail={me?.gmail}
                    onClose={() => setConsentFor(null)} onTracked={() => setConsentFor(null)} />
            )}
        </div>
    )
}

export default Jobs
