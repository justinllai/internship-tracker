// ============================================================
// Register.js — The registration page component
// This is what new users see when they want to create an account.
// It collects email, username, and password, sends them to our
// FastAPI backend, and redirects to login on success.
// ============================================================

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

function Register() {

    // --------------------------------------------------------
    // STATE
    // --------------------------------------------------------

    const [email, setEmail] = useState('')
    const [username, setUsername] = useState('')
    const [password, setPassword] = useState('')
    const [error, setError] = useState(null)
    const [success, setSuccess] = useState(false)
    const [loading, setLoading] = useState(false)
    const navigate = useNavigate()


    // --------------------------------------------------------
    // HANDLE SUBMIT
    // --------------------------------------------------------

    async function handleSubmit(e) {
        e.preventDefault()
        setError(null)
        setLoading(true)

        try {
            const response = await fetch('http://localhost:8000/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ email, username, password })
            })

            const data = await response.json()

            if (response.ok) {
                // Registration succeeded — show success message
                // We don't auto-login here, we send them to login page
                setSuccess(true)
            } else {
                setError(data.detail || 'Registration failed')
            }

        } catch (err) {
            setError('Could not connect to server. Is the backend running?')
        } finally {
            setLoading(false)
        }
    }


    // --------------------------------------------------------
    // JSX
    // --------------------------------------------------------

    // If registration succeeded show a success message
    if (success) {
        return (
            <div style={styles.container}>
                <div style={styles.card}>
                    <h1 style={styles.title}>Account Created!</h1>
                    <p style={styles.successText}>
                        Your account has been created successfully.
                    </p>
                    <button
                        style={styles.button}
                        onClick={() => navigate('/')}
                    >
                        Go to Login
                    </button>
                </div>
            </div>
        )
    }

    return (
        <div style={styles.container}>
            <div style={styles.card}>
                <h1 style={styles.title}>Internship Tracker</h1>
                <h2 style={styles.subtitle}>Create Account</h2>

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
                            onChange={(e) => setEmail(e.target.value)}
                            style={styles.input}
                            placeholder="you@example.com"
                            required
                        />
                    </div>

                    <div style={styles.field}>
                        <label style={styles.label}>Username</label>
                        <input
                            type="text"
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            style={styles.input}
                            placeholder="cooluser123"
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
                            placeholder="Choose a strong password"
                            required
                        />
                    </div>

                    <button
                        type="submit"
                        style={loading ? styles.buttonDisabled : styles.button}
                        disabled={loading}
                    >
                        {loading ? 'Creating account...' : 'Create Account'}
                    </button>

                </form>

                <p style={styles.switchText}>
                    Already have an account?{' '}
                    <span
                        style={styles.link}
                        onClick={() => navigate('/')}
                    >
                        Sign in
                    </span>
                </p>
            </div>
        </div>
    )
}


// --------------------------------------------------------
// STYLES
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
    successText: {
        textAlign: 'center',
        color: '#16a34a',
        marginBottom: '24px'
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

export default Register