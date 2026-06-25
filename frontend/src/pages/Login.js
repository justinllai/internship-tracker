// ============================================================
// Login.js — The login page component
// This is what users see when they want to sign in.
// It collects email and password, sends them to our FastAPI
// backend, and stores the JWT token if login succeeds.
// ============================================================

// useState lets us store and update data inside the component
// useEffect would let us run code when the component loads (not needed here yet)
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

function Login() {

    // --------------------------------------------------------
    // STATE — Data that can change and affects what's displayed
    // --------------------------------------------------------

    // email: stores whatever the user types in the email field
    // setEmail: the function we call to update it
    // useState('') means it starts as an empty string
    const [email, setEmail] = useState('')

    // password: stores whatever the user types in the password field
    const [password, setPassword] = useState('')

    // error: stores any error message to show the user
    // null means no error right now
    const [error, setError] = useState(null)

    // loading: tracks if we're waiting for the backend to respond
    // We use this to disable the button while the request is in flight
    const [loading, setLoading] = useState(false)
    const navigate = useNavigate()


    // --------------------------------------------------------
    // HANDLE SUBMIT — Runs when the user clicks "Login"
    // --------------------------------------------------------

    async function handleSubmit(e) {
        // e.preventDefault() stops the page from refreshing.
        // By default HTML forms reload the page on submit —
        // we don't want that in React.
        e.preventDefault()

        // Clear any previous error and show loading state
        setError(null)
        setLoading(true)

        try {
            // Send a POST request to our FastAPI /login endpoint
            // This is the same request we made in PowerShell, but from React
            const response = await fetch('http://localhost:8000/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                // Convert our state values to JSON to send to the backend
                body: JSON.stringify({ email, password })
            })

            // Parse the JSON response from the backend
            const data = await response.json()

            if (response.ok) {
                // response.ok means status 200 — login succeeded!
                // Store the JWT token in localStorage so we can use it
                // on future requests without logging in again.
                // localStorage persists even if the page refreshes.
                localStorage.setItem('token', data.access_token)

                // For now just alert — we'll add proper navigation later
                alert('Login successful! Dashboard coming soon.')
            } else {
                // response not ok means login failed
                // data.detail is the error message from FastAPI
                setError(data.detail || 'Login failed')
            }

        } catch (err) {
            // This catches network errors — like if the backend is down
            setError('Could not connect to server. Is the backend running?')
        } finally {
            // Always runs — whether success or error
            // Turn off loading state so button becomes clickable again
            setLoading(false)
        }
    }


    // --------------------------------------------------------
    // JSX — What gets displayed on screen
    // JSX looks like HTML but it's actually JavaScript.
    // Differences: className instead of class, onClick instead of onclick
    // --------------------------------------------------------

    return (
        <div style={styles.container}>
            <div style={styles.card}>
                <h1 style={styles.title}>Internship Tracker</h1>
                <h2 style={styles.subtitle}>Sign In</h2>

                {/* Show error message if there is one */}
                {/* In JSX, {expression} lets you write JavaScript inside HTML */}
                {error && (
                    <div style={styles.error}>
                        {error}
                    </div>
                )}

                <form onSubmit={handleSubmit} style={styles.form}>

                    <div style={styles.field}>
                        <label style={styles.label}>Email</label>
                        <input
                            type="email"
                            value={email}
                            // onChange fires every time the user types a character
                            // e.target.value is the current value of the input
                            onChange={(e) => setEmail(e.target.value)}
                            style={styles.input}
                            placeholder="you@example.com"
                            required
                        />
                    </div>

                    <div style={styles.field}>
                        <label style={styles.label}>Password</label>
                        <input
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            style={styles.input}
                            placeholder="Your password"
                            required
                        />
                    </div>

                    {/* disabled={loading} grays out the button while waiting */}
                    <button
                        type="submit"
                        style={loading ? styles.buttonDisabled : styles.button}
                        disabled={loading}
                    >
                        {loading ? 'Signing in...' : 'Sign In'}
                    </button>

                </form>

                <p style={styles.switchText}>
                    Don't have an account?{' '}
                    <span
                        style={styles.link}
                        onClick={() => navigate('/register')}
                    >
                        Sign up
                    </span>
                </p>
            </div>
        </div>
    )
}


// --------------------------------------------------------
// STYLES — Inline styles to make the page look decent
// We'll replace this with proper CSS later
// --------------------------------------------------------

const styles = {
    container: {
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '100vh',
        backgroundColor: '#f0f2f5'
    },
    card: {
        backgroundColor: 'white',
        padding: '40px',
        borderRadius: '12px',
        boxShadow: '0 2px 20px rgba(0,0,0,0.1)',
        width: '100%',
        maxWidth: '400px'
    },
    title: {
        textAlign: 'center',
        color: '#1a1a2e',
        marginBottom: '4px',
        fontSize: '24px'
    },
    subtitle: {
        textAlign: 'center',
        color: '#666',
        marginBottom: '24px',
        fontSize: '16px',
        fontWeight: 'normal'
    },
    form: {
        display: 'flex',
        flexDirection: 'column',
        gap: '16px'
    },
    field: {
        display: 'flex',
        flexDirection: 'column',
        gap: '6px'
    },
    label: {
        fontSize: '14px',
        fontWeight: '600',
        color: '#333'
    },
    input: {
        padding: '10px 14px',
        borderRadius: '8px',
        border: '1px solid #ddd',
        fontSize: '14px',
        outline: 'none'
    },
    button: {
        padding: '12px',
        backgroundColor: '#4f46e5',
        color: 'white',
        border: 'none',
        borderRadius: '8px',
        fontSize: '15px',
        fontWeight: '600',
        cursor: 'pointer',
        marginTop: '8px'
    },
    buttonDisabled: {
        padding: '12px',
        backgroundColor: '#a5b4fc',
        color: 'white',
        border: 'none',
        borderRadius: '8px',
        fontSize: '15px',
        fontWeight: '600',
        cursor: 'not-allowed',
        marginTop: '8px'
    },
    error: {
        backgroundColor: '#fee2e2',
        color: '#dc2626',
        padding: '10px 14px',
        borderRadius: '8px',
        fontSize: '14px',
        marginBottom: '16px'
    },
    switchText: {
        textAlign: 'center',
        marginTop: '20px',
        fontSize: '14px',
        color: '#666'
    },
    link: {
        color: '#4f46e5',
        cursor: 'pointer',
        fontWeight: '600'
    }
}

export default Login