// ============================================================
// AppShell.js — The frame around every logged-in page
// ------------------------------------------------------------
// Sticky top nav (brand, search, icon links with a live
// notification badge) + the current page + a toast for new
// inbox updates.
//
// <Outlet /> is React Router's "slot": nested routes in App.js
// render their page component right there. So the nav is
// written once and every page gets it automatically.
// ============================================================

import { useState } from 'react'
import { NavLink, Outlet, useNavigate, Link } from 'react-router-dom'
import { clearToken } from '../api'
import { SessionProvider, useSession } from '../context/SessionContext'
import { BellIcon, BriefcaseIcon, GearIcon, LogoMark, LogoutIcon, MailIcon, SearchIcon, TrackerIcon, CloseIcon } from './Icons'

function NavItem({ to, icon, label, badge }) {
    return (
        // NavLink adds the "active" class automatically when the URL matches
        <NavLink to={to} className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}>
            {icon}
            <span className="label">{label}</span>
            {badge > 0 && (
                <span className="badge" aria-label={`${badge} unread`}>{badge > 99 ? '99+' : badge}</span>
            )}
        </NavLink>
    )
}

function NavBar() {
    const { unreadCount } = useSession()
    const [query, setQuery] = useState('')
    const navigate = useNavigate()

    function handleSearch(e) {
        e.preventDefault()
        // The global search box searches internships near you
        navigate(`/jobs?q=${encodeURIComponent(query.trim() || 'software engineer')}`)
    }

    function handleLogout() {
        clearToken()
        navigate('/')
    }

    return (
        <header className="nav">
            <div className="nav-inner">
                <Link to="/dashboard" className="brand" aria-label="Internship Tracker home">
                    <span className="brand-mark"><LogoMark /></span>
                    <span className="brand-name">Internship Tracker</span>
                </Link>

                <form className="nav-search" onSubmit={handleSearch} role="search">
                    <SearchIcon />
                    <label htmlFor="nav-search" className="sr-only">Search internships</label>
                    <input id="nav-search" placeholder="Search internships" value={query}
                        onChange={(e) => setQuery(e.target.value)} />
                </form>

                <nav className="nav-links" aria-label="Main">
                    <NavItem to="/dashboard" icon={<TrackerIcon />} label="Tracker" />
                    <NavItem to="/jobs" icon={<BriefcaseIcon />} label="Jobs" />
                    <NavItem to="/notifications" icon={<BellIcon />} label="Updates" badge={unreadCount} />
                    <NavItem to="/settings" icon={<GearIcon />} label="Settings" />
                    <button className="nav-link nav-button" onClick={handleLogout}>
                        <LogoutIcon />
                        <span className="label">Sign out</span>
                    </button>
                </nav>
            </div>
        </header>
    )
}

function Toast() {
    const { toast, setToast } = useSession()
    const navigate = useNavigate()
    if (!toast) return null
    return (
        // role="status" makes screen readers announce it politely
        <div className="toast" role="status">
            <span className="notif-icon" style={{ background: 'var(--brand-soft)', color: 'var(--brand)' }}><MailIcon /></span>
            <div style={{ flex: 1 }}>
                <div className="bold">{toast}</div>
                <button className="btn btn-ghost btn-sm" style={{ paddingLeft: 0 }}
                    onClick={() => { setToast(null); navigate('/notifications') }}>
                    View updates
                </button>
            </div>
            <button className="icon-btn" aria-label="Dismiss" onClick={() => setToast(null)}><CloseIcon size={16} /></button>
        </div>
    )
}

function AppShell() {
    return (
        <SessionProvider>
            <NavBar />
            <main>
                <Outlet />
            </main>
            <Toast />
        </SessionProvider>
    )
}

export default AppShell
