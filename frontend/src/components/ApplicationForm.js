// ============================================================
// ApplicationForm.js — Add or edit an application (in a modal)
// The same component handles both: if `initial` has an id we're
// editing (PUT), otherwise creating (POST).
// This is a "controlled form": every input's value lives in
// React state, so React is the single source of truth.
// ============================================================

import { useState } from 'react'
import { api } from '../api'
import { STATUSES } from '../constants'
import Modal from './Modal'

const EMPTY = {
    company_name: '', position: '', status: 'Applied', location: '',
    job_url: '', company_domain: '', deadline: '', notes: '',
}

// The backend sends ISO datetimes; <input type="date"> wants YYYY-MM-DD
function toDateInput(iso) {
    return iso ? iso.slice(0, 10) : ''
}

function ApplicationForm({ initial, onClose, onSaved }) {
    const editing = Boolean(initial?.id)
    const [form, setForm] = useState(() => ({
        ...EMPTY,
        ...(initial || {}),
        deadline: toDateInput(initial?.deadline),
        location: initial?.location || '',
        job_url: initial?.job_url || '',
        company_domain: initial?.company_domain || '',
        notes: initial?.notes || '',
    }))
    const [busy, setBusy] = useState(false)
    const [error, setError] = useState(null)

    // One change handler for every field: uses the input's `name`
    function update(e) {
        setForm({ ...form, [e.target.name]: e.target.value })
    }

    async function handleSubmit(e) {
        e.preventDefault()
        setBusy(true)
        setError(null)
        // Send empty strings as null so the DB stores "no value"
        const payload = {
            company_name: form.company_name.trim(),
            position: form.position.trim(),
            status: form.status,
            location: form.location.trim() || null,
            job_url: form.job_url.trim() || null,
            company_domain: form.company_domain.trim() || null,
            deadline: form.deadline ? `${form.deadline}T00:00:00` : null,
            notes: form.notes.trim() || null,
        }
        try {
            const saved = editing
                ? await api.updateApplication(initial.id, payload)
                : await api.createApplication({ ...payload, source: initial?.source || 'manual' })
            onSaved(saved, { created: !editing })
        } catch (err) {
            setError(err.message)
            setBusy(false)
        }
    }

    return (
        <Modal title={editing ? 'Edit application' : 'Add an application'} onClose={onClose}
            footer={<>
                <button className="btn btn-ghost" onClick={onClose} type="button">Cancel</button>
                <button className="btn btn-primary" type="submit" form="application-form" disabled={busy}>
                    {busy ? 'Saving…' : 'Save'}
                </button>
            </>}>
            {error && <div className="alert alert-error" role="alert">{error}</div>}
            <form id="application-form" className="form-grid" onSubmit={handleSubmit}>
                <div className="field">
                    <label htmlFor="f-company">Company *</label>
                    <input id="f-company" name="company_name" className="input" required maxLength={120}
                        value={form.company_name} onChange={update} autoFocus />
                </div>
                <div className="field">
                    <label htmlFor="f-position">Position *</label>
                    <input id="f-position" name="position" className="input" required maxLength={160}
                        value={form.position} onChange={update} />
                </div>
                <div className="field">
                    <label htmlFor="f-status">Status</label>
                    <select id="f-status" name="status" className="select" value={form.status} onChange={update}>
                        {STATUSES.map(s => <option key={s}>{s}</option>)}
                    </select>
                </div>
                <div className="field">
                    <label htmlFor="f-location">Location</label>
                    <input id="f-location" name="location" className="input" placeholder="San Jose, CA / Remote"
                        value={form.location} onChange={update} />
                </div>
                <div className="field">
                    <label htmlFor="f-domain">Company email domain</label>
                    <input id="f-domain" name="company_domain" className="input" placeholder="stripe.com"
                        value={form.company_domain} onChange={update} />
                </div>
                <div className="field">
                    <label htmlFor="f-deadline">Deadline</label>
                    <input id="f-deadline" name="deadline" type="date" className="input"
                        value={form.deadline} onChange={update} />
                </div>
                <div className="field span-2">
                    <label htmlFor="f-url">Job posting link</label>
                    <input id="f-url" name="job_url" type="url" className="input" placeholder="https://…"
                        value={form.job_url} onChange={update} />
                </div>
                <div className="field span-2">
                    <label htmlFor="f-notes">Notes</label>
                    <textarea id="f-notes" name="notes" className="textarea" maxLength={2000}
                        value={form.notes} onChange={update} />
                </div>
            </form>
        </Modal>
    )
}

export default ApplicationForm
