# ============================================================
# classifier.py — Guess what a company email means
# ------------------------------------------------------------
# Input: subject + Gmail's short preview snippet.
# Output: offer | interview | rejection | acknowledgment | other
#
# Approach: a SCORED keyword system.
#   - "strong" phrases are near-certain signals  → 2 points
#   - "weak" words are hints                     → 1 point
#   - a category needs 2+ points to win
# So "unfortunately" alone (weak) can't mark a rejection —
# "Unfortunately the interviewer needs to reschedule" is NOT a
# rejection — but "unfortunately ... other candidates" is.
#
# Order of precedence: offer > rejection > interview > ack.
# Rejection beats interview because rejections often mention the
# interview you had ("thank you for interviewing ... unfortunately
# we have decided to move forward with other candidates").
#
# Why rules instead of machine learning / an LLM?
#   - Explainable: we can say exactly why an email got its label.
#   - Testable: tests/test_classifier.py pins down real examples.
#   - Free, instant, and the email text never leaves our server.
# And because rules WILL sometimes be wrong, the app only
# SUGGESTS a status change; the user confirms it.
# ============================================================

import re
from typing import Optional, Tuple

OFFER_STRONG = [
    "offer letter", "extend an offer", "extend you an offer", "pleased to offer you the",
    "pleased to offer you a position", "pleased to offer you an internship", "offer of employment",
    "internship offer", "job offer", "formal offer", "congratulations on your offer",
]

REJECTION_STRONG = [
    "not moving forward", "not be moving forward", "will not be proceeding", "decided not to proceed",
    "other candidates", "other applicants", "regret to inform", "not been selected", "were not selected",
    "was not selected", "position has been filled", "no longer under consideration", "not to move forward",
    "unable to offer you", "won't be moving forward", "will not be advancing",
]
REJECTION_WEAK = ["unfortunately", "after careful consideration", "we appreciate your interest"]

INTERVIEW_STRONG = [
    "schedule an interview", "schedule a call", "invite you to interview", "invitation to interview",
    "interview invitation", "offer you an interview", "phone screen", "technical interview",
    "coding challenge", "online assessment", "hackerrank", "codesignal", "your availability",
    "book a time", "calendly", "next round", "move you forward", "moving you forward",
    "would like to speak with you", "set up a time",
]
INTERVIEW_WEAK = ["interview", "next steps", "chat", "assessment"]

ACK_PHRASES = [
    "thank you for applying", "thanks for applying", "received your application",
    "application has been received", "application received", "thank you for your application",
    "we have received your", "application was submitted", "thank you for your interest",
]

# What status each label SUGGESTS (None = no change suggested)
SUGGESTED_STATUS = {
    "offer": "Offer",
    "interview": "Interview",
    "rejection": "Rejected",
    "acknowledgment": None,
    "other": None,
}


def _normalize(text: str) -> str:
    # lowercase, curly apostrophes → straight, collapse whitespace
    text = text.lower().replace("’", "'")
    return re.sub(r"\s+", " ", text)


def _score(text: str, strong, weak=()) -> int:
    return sum(2 for p in strong if p in text) + sum(1 for w in weak if re.search(rf"\b{re.escape(w)}\b", text))


def classify(subject: str, snippet: str = "") -> Tuple[str, Optional[str]]:
    """Return (label, suggested_status)."""
    text = _normalize(f"{subject or ''} . {snippet or ''}")
    is_ack = any(p in text for p in ACK_PHRASES)

    if _score(text, OFFER_STRONG) >= 2:
        label = "offer"
    elif _score(text, REJECTION_STRONG, REJECTION_WEAK) >= 2:
        label = "rejection"
    elif _score(text, INTERVIEW_STRONG) >= 2:
        label = "interview"
    # Acknowledgments often say "next steps ... if we'd like to
    # interview you" — weak interview words alone must NOT beat an
    # acknowledgment phrase.
    elif is_ack:
        label = "acknowledgment"
    elif _score(text, INTERVIEW_STRONG, INTERVIEW_WEAK) >= 2:
        label = "interview"
    else:
        label = "other"
    return label, SUGGESTED_STATUS[label]
