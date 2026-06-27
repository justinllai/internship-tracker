// ============================================================
// Dashboard.js — The main page after login
// This is where users see and manage all their applications.
// It's a protected page — if you're not logged in you get
// redirected to the login page automatically.
// ============================================================

import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

function Dashboard() {

    // --------------------------------------------------------
    // STATE
    // --------------------------------------------------------

    // applications: the list of applications from the backend
    const [applications, setApplications] = useState([])

    // loading: true while we're fetching from the backend
    const [loading, setLoading] = useState(true)

    // error: any error message to show the user
    const [error, setError] = useState(null)

    // showForm: controls whether the "Add Application" form is visible
    const [showForm, setShowForm] = useState(false)

    // newApp: the data for the new application being created
    const [newApp, setNewApp] = useState({
        company_name: '',
        position: '',
        status: 'Applied',
        notes: ''
    })

    const navigate = useNavigate()


    // --------------------------------------------------------
    // useEffect — Runs when the component first loads
    // Think of it like "on page load, do this"
    // The empty [] at the end means "only run once on mount"
    // --------------------------------------------------------

    useEffect(() => {
        // Step 1: Check if user is logged in
        const token = localStorage.getItem('token')
        if (!token) {
            // No token means not logged in — redirect to login
            navigate('/')
            return
        }

        // Step 2: Fetch their applications
        fetchApplications(token)
    }, [])


    // --------------------------------------------------------
    // FETCH APPLICATIONS — Gets all applications from backend
    // --------------------------------------------------------

    async function fetchApplications(token) {
        try {
            const response = await fetch('http://localhost:8000/applications', {
                method: 'GET',
                headers: {
                    // This is how we send the token to the backend
                    // Same as "Authorization: Bearer <token>" in PowerShell
                    'Authorization': `Bearer ${token}`
                }
            })

            if (response.ok) {
                const data = await response.json()
                setApplications(data)
            } else if (response.status === 401) {
                // 401 means token expired or invalid
                // Clear the bad token and send them back to login
                localStorage.removeItem('token')
                navigate('/')
            } else {
                setError('Failed to load applications')
            }
        } catch (err) {
            setError('Could not connect to server')
        } finally {
            setLoading(false)
        }
    }


    // --------------------------------------------------------
    // CREATE APPLICATION — Sends new application to backend
    // --------------------------------------------------------

    async function handleCreateApp(e) {
        e.preventDefault()
        const token = localStorage.getItem('token')

        try {
            const response = await fetch('http://localhost:8000/applications', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(newApp)
            })

            if (response.ok) {
                const created = await response.json()
                // Add the new application to our list without refetching
                setApplications([...applications, created])
                // Reset the form
                setNewApp({ company_name: '', position: '', status: 'Applied', notes: '' })
                setShowForm(false)
            } else {
                setError('Failed to create application')
            }
        } catch (err) {
            setError('Could not connect to server')
        }
    }


    // --------------------------------------------------------
    // UPDATE STATUS — Changes status of an application
    // --------------------------------------------------------

    async function handleStatusChange(id, newStatus) {
        const token = localStorage.getItem('token')

        try {
            const response = await fetch(`http://localhost:8000/applications/${id}`, {
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ status: newStatus })
            })

            if (response.ok) {
                // Update the status in our local state without refetching
                setApplications(applications.map(app =>
                    app.id === id ? { ...app, status: newStatus } : app
                ))
            }
        } catch (err) {
            setError('Could not update status')
        }
    }


    // --------------------------------------------------------
    // DELETE APPLICATION
    // --------------------------------------------------------

    async function handleDelete(id) {
        const token = localStorage.getItem('token')

        try {
            const response = await fetch(`http://localhost:8000/applications/${id}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            })

            if (response.ok) {
                // Remove from local state without refetching
                setApplications(applications.filter(app => app.id !== id))
            }
        } catch (err) {
            setError('Could not delete application')
        }
    }


    // --------------------------------------------------------
    // LOGOUT
    // --------------------------------------------------------

    function handleLogout() {
        // Remove token from localStorage and redirect to login
        localStorage.removeItem('token')
        navigate('/')
    }


    // --------------------------------------------------------
    // STATUS COLOR — Returns a color based on status
    // --------------------------------------------------------

    function getStatusColor(status) {
        switch (status) {
            case 'Applied': return '#3b82f6'      // blue
            case 'Interview': return '#f59e0b'    // yellow
            case 'Offer': return '#10b981'        // green
            case 'Rejected': return '#ef4444'     // red
            default: return '#6b7280'             // gray
        }
    }


    // --------------------------------------------------------
    // JSX
    // --------------------------------------------------------

    if (loading) {
        return (
            <div style={styles.centered}>
                <p>Loading your applications...</p>
            </div>
        )
    }

    return (
        <div style={styles.container}>

            {/* HEADER */}
            <div style={styles.header}>
                <h1 style={styles.title}>Internship Tracker</h1>
                <button onClick={handleLogout} style={styles.logoutButton}>
                    Log Out
                </button>
            </div>

            {/* ERROR MESSAGE */}
            {error && (
                <div style={styles.error}>{error}</div>
            )}

            {/* STATS BAR */}
            <div style={styles.statsBar}>
                <div style={styles.stat}>
                    <span style={styles.statNumber}>{applications.length}</span>
                    <span style={styles.statLabel}>Total</span>
                </div>
                <div style={styles.stat}>
                    <span style={{...styles.statNumber, color: '#3b82f6'}}>
                        {applications.filter(a => a.status === 'Applied').length}
                    </span>
                    <span style={styles.statLabel}>Applied</span>
                </div>
                <div style={styles.stat}>
                    <span style={{...styles.statNumber, color: '#f59e0b'}}>
                        {applications.filter(a => a.status === 'Interview').length}
                    </span>
                    <span style={styles.statLabel}>Interview</span>
                </div>
                <div style={styles.stat}>
                    <span style={{...styles.statNumber, color: '#10b981'}}>
                        {applications.filter(a => a.status === 'Offer').length}
                    </span>
                    <span style={styles.statLabel}>Offer</span>
                </div>
                <div style={styles.stat}>
                    <span style={{...styles.statNumber, color: '#ef4444'}}>
                        {applications.filter(a => a.status === 'Rejected').length}
                    </span>
                    <span style={styles.statLabel}>Rejected</span>
                </div>
            </div>

            {/* ADD APPLICATION BUTTON */}
            <button
                onClick={() => setShowForm(!showForm)}
                style={styles.addButton}
            >
                {showForm ? 'Cancel' : '+ Add Application'}
            </button>

            {/* ADD APPLICATION FORM */}
            {showForm && (
                <div style={styles.formCard}>
                    <h2 style={styles.formTitle}>New Application</h2>
                    <form onSubmit={handleCreateApp} style={styles.form}>
                        <input
                            placeholder="Company Name *"
                            value={newApp.company_name}
                            onChange={(e) => setNewApp({...newApp, company_name: e.target.value})}
                            style={styles.input}
                            required
                        />
                        <input
                            placeholder="Position *"
                            value={newApp.position}
                            onChange={(e) => setNewApp({...newApp, position: e.target.value})}
                            style={styles.input}
                            required
                        />
                        <select
                            value={newApp.status}
                            onChange={(e) => setNewApp({...newApp, status: e.target.value})}
                            style={styles.input}
                        >
                            <option>Applied</option>
                            <option>Interview</option>
                            <option>Offer</option>
                            <option>Rejected</option>
                        </select>
                        <textarea
                            placeholder="Notes (optional)"
                            value={newApp.notes}
                            onChange={(e) => setNewApp({...newApp, notes: e.target.value})}
                            style={{...styles.input, height: '80px'}}
                        />
                        <button type="submit" style={styles.submitButton}>
                            Save Application
                        </button>
                    </form>
                </div>
            )}

            {/* APPLICATIONS LIST */}
            {applications.length === 0 ? (
                <div style={styles.emptyState}>
                    <p style={styles.emptyText}>No applications yet.</p>
                    <p style={styles.emptySubtext}>Click "+ Add Application" to get started!</p>
                </div>
            ) : (
                <div style={styles.list}>
                    {applications.map(app => (
                        <div key={app.id} style={styles.card}>
                            <div style={styles.cardHeader}>
                                <div>
                                    <h3 style={styles.company}>{app.company_name}</h3>
                                    <p style={styles.position}>{app.position}</p>
                                </div>
                                <span style={{
                                    ...styles.statusBadge,
                                    backgroundColor: getStatusColor(app.status)
                                }}>
                                    {app.status}
                                </span>
                            </div>

                            {app.notes && (
                                <p style={styles.notes}>{app.notes}</p>
                            )}

                            <div style={styles.cardFooter}>
                                <select
                                    value={app.status}
                                    onChange={(e) => handleStatusChange(app.id, e.target.value)}
                                    style={styles.statusSelect}
                                >
                                    <option>Applied</option>
                                    <option>Interview</option>
                                    <option>Offer</option>
                                    <option>Rejected</option>
                                </select>
                                <button
                                    onClick={() => handleDelete(app.id)}
                                    style={styles.deleteButton}
                                >
                                    Delete
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    )
}


// --------------------------------------------------------
// STYLES
// --------------------------------------------------------

const styles = {
    container: {
        maxWidth: '800px',
        margin: '0 auto',
        padding: '24px',
        fontFamily: 'sans-serif'
    },
    centered: {
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '100vh'
    },
    header: {
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '24px'
    },
    title: {
        fontSize: '24px',
        fontWeight: '700',
        color: '#1a1a2e'
    },
    logoutButton: {
        padding: '8px 16px',
        backgroundColor: 'transparent',
        border: '1px solid #ddd',
        borderRadius: '8px',
        cursor: 'pointer',
        fontSize: '14px',
        color: '#666'
    },
    statsBar: {
        display: 'flex',
        gap: '16px',
        backgroundColor: 'white',
        padding: '16px 24px',
        borderRadius: '12px',
        boxShadow: '0 1px 4px rgba(0,0,0,0.08)',
        marginBottom: '24px'
    },
    stat: {
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        flex: 1
    },
    statNumber: {
        fontSize: '28px',
        fontWeight: '700',
        color: '#1a1a2e'
    },
    statLabel: {
        fontSize: '12px',
        color: '#666',
        marginTop: '2px'
    },
    addButton: {
        padding: '10px 20px',
        backgroundColor: '#4f46e5',
        color: 'white',
        border: 'none',
        borderRadius: '8px',
        fontSize: '14px',
        fontWeight: '600',
        cursor: 'pointer',
        marginBottom: '16px'
    },
    formCard: {
        backgroundColor: 'white',
        padding: '24px',
        borderRadius: '12px',
        boxShadow: '0 1px 4px rgba(0,0,0,0.08)',
        marginBottom: '24px'
    },
    formTitle: {
        fontSize: '16px',
        fontWeight: '600',
        marginBottom: '16px',
        color: '#1a1a2e'
    },
    form: {
        display: 'flex',
        flexDirection: 'column',
        gap: '12px'
    },
    input: {
        padding: '10px 14px',
        borderRadius: '8px',
        border: '1px solid #ddd',
        fontSize: '14px',
        outline: 'none',
        width: '100%',
        boxSizing: 'border-box'
    },
    submitButton: {
        padding: '10px',
        backgroundColor: '#4f46e5',
        color: 'white',
        border: 'none',
        borderRadius: '8px',
        fontSize: '14px',
        fontWeight: '600',
        cursor: 'pointer'
    },
    emptyState: {
        textAlign: 'center',
        padding: '60px 0'
    },
    emptyText: {
        fontSize: '18px',
        color: '#333',
        marginBottom: '8px'
    },
    emptySubtext: {
        fontSize: '14px',
        color: '#666'
    },
    list: {
        display: 'flex',
        flexDirection: 'column',
        gap: '12px'
    },
    card: {
        backgroundColor: 'white',
        padding: '20px',
        borderRadius: '12px',
        boxShadow: '0 1px 4px rgba(0,0,0,0.08)'
    },
    cardHeader: {
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
        marginBottom: '8px'
    },
    company: {
        fontSize: '16px',
        fontWeight: '700',
        color: '#1a1a2e',
        margin: '0 0 4px 0'
    },
    position: {
        fontSize: '14px',
        color: '#666',
        margin: 0
    },
    statusBadge: {
        padding: '4px 12px',
        borderRadius: '20px',
        color: 'white',
        fontSize: '12px',
        fontWeight: '600'
    },
    notes: {
        fontSize: '13px',
        color: '#555',
        backgroundColor: '#f9f9f9',
        padding: '8px 12px',
        borderRadius: '6px',
        marginBottom: '12px'
    },
    cardFooter: {
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginTop: '12px'
    },
    statusSelect: {
        padding: '6px 10px',
        borderRadius: '6px',
        border: '1px solid #ddd',
        fontSize: '13px',
        cursor: 'pointer'
    },
    deleteButton: {
        padding: '6px 14px',
        backgroundColor: 'transparent',
        border: '1px solid #ef4444',
        color: '#ef4444',
        borderRadius: '6px',
        fontSize: '13px',
        cursor: 'pointer'
    },
    error: {
        backgroundColor: '#fee2e2',
        color: '#dc2626',
        padding: '10px 14px',
        borderRadius: '8px',
        fontSize: '14px',
        marginBottom: '16px'
    }
}

export default Dashboard