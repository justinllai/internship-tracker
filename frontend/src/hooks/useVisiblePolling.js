// ============================================================
// useVisiblePolling.js — "Live" updates via polling
// ------------------------------------------------------------
// Calls `callback` every `intervalMs`, but ONLY while the
// browser tab is visible. When you switch back to the tab it
// refreshes immediately.
//
// Why polling and not WebSockets / Server-Sent Events?
//   - New data only appears when the backend checks Gmail
//     (every few minutes), so a push channel wouldn't make
//     updates feel faster — it would just be more moving parts.
//   - Our free Render server sleeps when idle, which kills
//     long-lived connections anyway.
//   - Pausing while hidden means a forgotten background tab
//     doesn't hammer the server all day.
// If we later needed sub-second updates (chat, live prices),
// that's when WebSockets/SSE would earn their complexity.
//
// This is a "custom hook": a function starting with `use` that
// packages reusable stateful logic so any component can say
// useVisiblePolling(fn, 30000) instead of copying this code.
// ============================================================

import { useEffect, useRef } from 'react'

export function useVisiblePolling(callback, intervalMs, enabled = true) {
    // Keep the latest callback in a ref so the interval always
    // calls the newest version without re-creating the timer
    // on every render. (This is how you avoid the
    // exhaustive-deps "infinite loop" trap we hit on Vercel.)
    const savedCallback = useRef(callback)
    useEffect(() => {
        savedCallback.current = callback
    }, [callback])

    useEffect(() => {
        if (!enabled) return undefined

        let timerId = null

        const tick = () => {
            if (document.visibilityState === 'visible') savedCallback.current()
        }

        const start = () => {
            if (timerId === null) timerId = setInterval(tick, intervalMs)
        }
        const stop = () => {
            clearInterval(timerId)
            timerId = null
        }

        const onVisibilityChange = () => {
            if (document.visibilityState === 'visible') {
                tick()      // catch up right away
                start()
            } else {
                stop()      // don't poll a hidden tab
            }
        }

        tick()
        start()
        document.addEventListener('visibilitychange', onVisibilityChange)

        // Cleanup when the component unmounts or interval changes
        return () => {
            stop()
            document.removeEventListener('visibilitychange', onVisibilityChange)
        }
    }, [intervalMs, enabled])
}
