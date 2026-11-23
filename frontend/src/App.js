// ============================================================
// App.js — The root component with routing
// Think of this as the "traffic director" of our app.
// It maps every URL path to the correct page component.
//
// New structure:
//   - Public pages (/ and /register) render on their own.
//   - All logged-in pages are NESTED under one route whose
//     element is <ProtectedRoute><AppShell/></ProtectedRoute>.
//     That means the login check and the nav bar are written
//     once, and every page inside gets both for free.
// ============================================================

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'

import Login from './pages/Login'
import Register from './pages/Register'
import Tracker from './pages/Tracker'
import Jobs from './pages/Jobs'
import Notifications from './pages/Notifications'
import Settings from './pages/Settings'
import OAuthCallback from './pages/OAuthCallback'
import AppShell from './components/AppShell'
import ProtectedRoute from './components/ProtectedRoute'

function App() {
    return (
        <BrowserRouter>
            <Routes>
                {/* Public */}
                <Route path="/" element={<Login />} />
                <Route path="/register" element={<Register />} />

                {/* Protected — a "layout route" with no path of its own */}
                <Route element={<ProtectedRoute><AppShell /></ProtectedRoute>}>
                    <Route path="/dashboard" element={<Tracker />} />
                    <Route path="/jobs" element={<Jobs />} />
                    <Route path="/notifications" element={<Notifications />} />
                    <Route path="/settings" element={<Settings />} />
                    {/* Google redirects here after the Gmail consent screen */}
                    <Route path="/oauth/gmail" element={<OAuthCallback />} />
                </Route>

                {/* Anything else → login */}
                <Route path="*" element={<Navigate to="/" />} />
            </Routes>
        </BrowserRouter>
    )
}

export default App
