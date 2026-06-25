// ============================================================
// App.js — The root component with routing
// React Router lets us show different pages based on the URL
// without the browser actually reloading the page.
// This is called client-side routing.
// ============================================================

// BrowserRouter wraps our whole app and enables routing
// Routes holds all our route definitions
// Route maps a URL path to a component
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Login from './pages/Login'
import Register from './pages/Register'

function App() {
  return (
    // BrowserRouter enables routing for everything inside it
    <BrowserRouter>
      <Routes>
        {/* When user visits / show the Login page */}
        <Route path="/" element={<Login />} />

        {/* When user visits /register show the Register page */}
        <Route path="/register" element={<Register />} />

        {/* Any unknown URL redirects to login */}
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App