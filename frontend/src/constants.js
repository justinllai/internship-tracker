// ============================================================
// constants.js — Values shared across many components
// Keeping the status list in one place means the dropdowns,
// filters, badges and pipeline bar can never disagree.
// The backend validates the exact same list (schemas.py).
// ============================================================

// Order matters: this is the pipeline left → right.
// "Rejected" is a terminal state, not a step, so it's last.
export const STATUSES = ['Saved', 'Applied', 'Interview', 'Offer', 'Rejected']

// Steps shown in the progress bar on each card
export const PIPELINE = ['Saved', 'Applied', 'Interview', 'Offer']

// Deterministic "logo" color from a company name, so the same
// company always gets the same color without storing anything.
// (A tiny hash: sum char codes, pick from a palette.)
const LOGO_COLORS = ['#0a66c2', '#057642', '#915907', '#b24020', '#5f4bb6', '#007a87', '#c37d16', '#8f5849']
export function logoColor(name = '') {
    let sum = 0
    for (const ch of name) sum += ch.charCodeAt(0)
    return LOGO_COLORS[sum % LOGO_COLORS.length]
}

// "3d ago" style relative time — easier to scan than full dates.
export function timeAgo(isoString) {
    if (!isoString) return ''
    // Backend sends naive UTC timestamps (no "Z"); add it so the
    // browser doesn't misread them as local time.
    const hasZone = /Z$|[+-]\d\d:\d\d$/.test(isoString)
    const then = new Date(hasZone ? isoString : isoString + 'Z')
    const seconds = Math.max(0, (Date.now() - then.getTime()) / 1000)
    if (seconds < 60) return 'just now'
    const minutes = seconds / 60
    if (minutes < 60) return `${Math.floor(minutes)}m ago`
    const hours = minutes / 60
    if (hours < 24) return `${Math.floor(hours)}h ago`
    const days = hours / 24
    if (days < 30) return `${Math.floor(days)}d ago`
    return then.toLocaleDateString()
}
