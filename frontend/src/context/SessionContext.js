// ============================================================
// SessionContext.js — Data many pages need at once
// ------------------------------------------------------------
// The nav bar needs the unread-notification count, the tracker
// needs to know if Gmail is connected, settings needs the saved
// location... Passing all that down through props ("prop
// drilling") gets messy. React Context is a shared box any
// component inside <SessionProvider> can read with useSession().
//
// It holds:
//   - me:           the logged-in user + Gmail connection status
//   - unreadCount:  number for the bell badge (polled every 30s)
//   - toast:        a pop-up when a NEW company reply arrives
// ============================================================

import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import { api } from '../api'
import { useVisiblePolling } from '../hooks/useVisiblePolling'

const SessionContext = createContext(null)

const POLL_MS = 30000

export function SessionProvider({ children }) {
    const [me, setMe] = useState(null)
    const [unreadCount, setUnreadCount] = useState(0)
    const [toast, setToast] = useState(null)
    // useRef holds a value that survives re-renders WITHOUT
    // causing one — perfect for "what was the count last time?"
    const lastCount = useRef(null)

    const refreshMe = useCallback(async () => {
        try {
            setMe(await api.me())
        } catch {
            // 401s are handled globally in api.js; other errors
            // just leave the previous value in place.
        }
    }, [])

    const refreshUnread = useCallback(async () => {
        try {
            const { count } = await api.unreadCount()
            // Show a toast only when the count goes UP after the
            // first load (not on initial page load).
            if (lastCount.current !== null && count > lastCount.current) {
                const diff = count - lastCount.current
                setToast(`${diff} new application update${diff > 1 ? 's' : ''} from your inbox`)
            }
            lastCount.current = count
            setUnreadCount(count)
        } catch {
            /* ignore transient errors while polling */
        }
    }, [])

    useEffect(() => {
        refreshMe()
    }, [refreshMe])

    // The "live" part: poll the cheap unread-count endpoint
    useVisiblePolling(refreshUnread, POLL_MS)

    // Auto-hide the toast after 6 seconds
    useEffect(() => {
        if (!toast) return undefined
        const id = setTimeout(() => setToast(null), 6000)
        return () => clearTimeout(id)
    }, [toast])

    const value = { me, refreshMe, unreadCount, refreshUnread, toast, setToast }
    return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>
}

export function useSession() {
    const ctx = useContext(SessionContext)
    if (!ctx) throw new Error('useSession must be used inside <SessionProvider>')
    return ctx
}
