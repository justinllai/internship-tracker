// ============================================================
// AuthLayout.js — Shared layout for Login and Register
// Left: headline + form. Right: what the app does.
// Login and Register used to duplicate ~100 lines of styles;
// now both pass their form in as `children`.
// ============================================================

import { Link } from 'react-router-dom'
import { BellIcon, BriefcaseIcon, LogoMark, ShieldIcon } from './Icons'

const FEATURES = [
    { icon: <BriefcaseIcon />, title: 'Find internships near you', text: 'Share your location or type a city — we search open internship postings in your area.' },
    { icon: <BellIcon />, title: 'Know the moment a company replies', text: 'Optionally connect Gmail and we watch only for replies from companies you applied to.' },
    { icon: <ShieldIcon />, title: 'Private by design', text: 'We store your city, never your address. We read sender + subject, never full emails. Disconnect anytime.' },
]

function AuthLayout({ headline, children, switchText, switchTo, switchLabel }) {
    return (
        <div className="auth-page">
            <div className="auth-top">
                <Link to="/" className="brand">
                    <span className="brand-mark"><LogoMark /></span>
                    <span>Internship Tracker</span>
                </Link>
            </div>
            <div className="auth-hero">
                <div>
                    <h1>{headline}</h1>
                    {children}
                    <p className="auth-switch">
                        {switchText} <Link to={switchTo} className="bold">{switchLabel}</Link>
                    </p>
                </div>
                <div className="auth-art">
                    {FEATURES.map(f => (
                        <div className="auth-feature" key={f.title}>
                            <span className="notif-icon">{f.icon}</span>
                            <div>
                                <div className="bold">{f.title}</div>
                                <div className="muted">{f.text}</div>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    )
}

export default AuthLayout
