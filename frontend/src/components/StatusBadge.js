// StatusBadge — colored pill for an application status.
// The color comes from CSS classes (status-applied, status-offer...)
// defined in index.css, so the colors adapt to dark mode for free.
function StatusBadge({ status }) {
    return <span className={`status status-${status.toLowerCase()}`}>{status}</span>
}

export default StatusBadge
