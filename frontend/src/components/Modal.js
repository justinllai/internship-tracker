// ============================================================
// Modal.js — Reusable dialog box
// Accessibility details that matter (and interviewers ask about):
//   - role="dialog" + aria-modal tells screen readers it's a dialog
//   - aria-labelledby points at the title so it gets announced
//   - Escape key closes it (keyboard users can't "click outside")
//   - Clicking the dark backdrop closes it; clicks inside don't
//     bubble up thanks to e.stopPropagation()
// ============================================================

import { useEffect, useId } from 'react'
import { CloseIcon } from './Icons'

function Modal({ title, onClose, children, footer }) {
    const titleId = useId()

    useEffect(() => {
        function onKey(e) {
            if (e.key === 'Escape') onClose()
        }
        document.addEventListener('keydown', onKey)
        // Cleanup function: React runs this when the modal unmounts,
        // so we don't leave a stray listener behind (a memory leak).
        return () => document.removeEventListener('keydown', onKey)
    }, [onClose])

    return (
        <div className="modal-backdrop" onClick={onClose}>
            <div className="card modal" role="dialog" aria-modal="true" aria-labelledby={titleId}
                onClick={(e) => e.stopPropagation()}>
                <div className="modal-header">
                    <h2 id={titleId}>{title}</h2>
                    <button className="icon-btn" onClick={onClose} aria-label="Close"><CloseIcon size={20} /></button>
                </div>
                <div className="modal-body">{children}</div>
                {footer && <div className="modal-footer">{footer}</div>}
            </div>
        </div>
    )
}

export default Modal
