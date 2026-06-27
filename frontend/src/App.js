// ============================================================
// App.js — The root component with routing
// Think of this as the "traffic director" of our app.
// It maps every URL path to the correct page component.
// When the URL changes, React Router swaps the component
// without reloading the browser — this is client-side routing.
// ============================================================

// BrowserRouter — wraps the whole app and enables URL-based routing
// Routes — container that holds all route definitions
// Route — maps a specific URL path to a component
// Navigate — programmatically redirects to another URL
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'

// Import all our page components
import Login from './pages/Login'
import Register from './pages/Register'

// We added Dashboard here because we built the Dashboard page
// and need to tell the router it exists at /dashboard
import Dashboard from './pages/Dashboard'

function App() {
  return (
    // BrowserRouter enables routing for everything inside it
    // Without this wrapper, useNavigate and Route won't work
    <BrowserRouter>
      <Routes>
        {/* / → Login page (the default landing page) */}
        <Route path="/" element={<Login />} />

        {/* /register → Register page for new users */}
        <Route path="/register" element={<Register />} />

        {/* /dashboard → Main app page after login
            This is a protected page — Dashboard.js checks
            for a token and redirects to / if none exists */}
        <Route path="/dashboard" element={<Dashboard />} />

        {/* * matches any URL we haven't defined above
            Instead of showing a blank page, redirect to login */}
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App