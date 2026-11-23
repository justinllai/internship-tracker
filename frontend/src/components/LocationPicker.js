// ============================================================
// LocationPicker.js — Choose "where" to search, safely
// ------------------------------------------------------------
// Two ways to set a location:
//
//  A) "Use my current location" — the browser Geolocation API.
//     Safety choices:
//       - We explain WHY before the browser shows its prompt.
//       - enableHighAccuracy: false → coarse Wi-Fi/cell position,
//         not GPS. We only need the city.
//       - We round to 2 decimals (~1.1 km) BEFORE sending, so a
//         precise position never leaves the device. The backend
//         rounds again (defense in depth) and only returns a
//         "City, ST" label. Coordinates are never stored.
//       - Geolocation only works on HTTPS (or localhost) — the
//         browser enforces that, so we check isSecureContext.
//
//  B) Type a city, ZIP, or even a full address.
//     The backend geocodes it and returns ONLY "City, ST".
//     The street address is used once and thrown away.
//
// The parent decides what to do with the label (search jobs,
// save as default) via the onChange callback.
// ============================================================

import { useState } from 'react'
import { api } from '../api'
import { LocateIcon, PinIcon } from './Icons'

// Turn GeolocationPositionError codes into helpful messages
const GEO_ERRORS = {
    1: 'Location permission was denied. No problem — type your city or ZIP instead.',
    2: "Your device couldn't determine a location. Try typing your city instead.",
    3: 'Getting your location took too long. Try again or type your city.',
}

function round2(n) {
    return Math.round(n * 100) / 100
}

function LocationPicker({ value, onChange }) {
    const [typed, setTyped] = useState('')
    const [busy, setBusy] = useState(false)
    const [error, setError] = useState(null)
    const [explained, setExplained] = useState(false)

    function useDeviceLocation() {
        setError(null)
        if (!('geolocation' in navigator) || !window.isSecureContext) {
            setError('Location access needs a secure (https) connection in a supported browser. Type your city instead.')
            return
        }
        setBusy(true)
        navigator.geolocation.getCurrentPosition(
            async (position) => {
                try {
                    const lat = round2(position.coords.latitude)
                    const lng = round2(position.coords.longitude)
                    const place = await api.resolveCoords(lat, lng)
                    onChange(place.label)
                    setExplained(false)
                } catch (err) {
                    setError(err.message)
                } finally {
                    setBusy(false)
                }
            },
            (geoError) => {
                setError(GEO_ERRORS[geoError.code] || 'Could not get your location.')
                setBusy(false)
            },
            // maximumAge: reuse a position up to 10 min old (no new fix needed)
            { enableHighAccuracy: false, timeout: 10000, maximumAge: 600000 }
        )
    }

    async function handleTyped(e) {
        e.preventDefault()
        if (!typed.trim()) return
        setError(null)
        setBusy(true)
        try {
            const place = await api.resolveQuery(typed.trim())
            onChange(place.label)
            setTyped('')   // drop the raw text (could be a home address)
        } catch (err) {
            setError(err.message)
        } finally {
            setBusy(false)
        }
    }

    return (
        <div className="stack">
            {value && (
                <div className="row">
                    <span className="tag"><PinIcon /> Searching near</span>
                    <span className="status status-applied">{value}</span>
                </div>
            )}

            {/* Step 1: explain, Step 2: browser prompt */}
            {!explained ? (
                <button type="button" className="btn btn-outline" onClick={() => setExplained(true)} disabled={busy}>
                    <LocateIcon /> Use my current location
                </button>
            ) : (
                <div className="alert alert-info">
                    <div className="stack" style={{ gap: 8 }}>
                        <div>
                            Your browser will ask for permission. We only use your approximate position
                            (about 1 km) to look up your <strong>city</strong> — we never store coordinates.
                        </div>
                        <div className="row">
                            <button type="button" className="btn btn-primary btn-sm" onClick={useDeviceLocation} disabled={busy}>
                                {busy ? 'Locating…' : 'Continue'}
                            </button>
                            <button type="button" className="btn btn-ghost btn-sm" onClick={() => setExplained(false)}>Cancel</button>
                        </div>
                    </div>
                </div>
            )}

            <form onSubmit={handleTyped} className="stack" style={{ gap: 6 }}>
                <label htmlFor="loc-typed" className="hint">…or enter a city, ZIP, or address (we only keep the city)</label>
                <div className="row" style={{ flexWrap: 'nowrap' }}>
                    <input id="loc-typed" className="input" placeholder="e.g. San Jose, CA or 95112"
                        value={typed} onChange={(e) => setTyped(e.target.value)} autoComplete="off" />
                    <button className="btn btn-primary" type="submit" disabled={busy || !typed.trim()}>Set</button>
                </div>
            </form>

            {error && <div className="alert alert-error" role="alert">{error}</div>}

            {/* Required attribution under OpenStreetMap's Nominatim usage policy */}
            <span className="hint">
                Location lookup © <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap contributors</a>
            </span>
        </div>
    )
}

export default LocationPicker
