// ============================================================
// ProtectedRoute.js — Guards pages that need a login
// Before: Dashboard.js checked for a token inside its own
// useEffect. Every new protected page would need to copy that.
// Now: wrap routes in <ProtectedRoute> once (see App.js).
//
// Important: this is a UX convenience, NOT security. Anyone can
// edit localStorage. Real security is the backend rejecting
// requests without a valid JWT (get_current_user in deps.py).
// ============================================================

import { Navigate } from 'react-router-dom'
import { getToken } from '../api'

function ProtectedRoute({ children }) {
    if (!getToken()) return <Navigate to="/" replace />
    return children
}

export default ProtectedRoute
