# ============================================================
# email_matching.py — "Is this email from a company I applied to?"
# ------------------------------------------------------------
# Three ways an email can match an application:
#
#  1. Company domain — sender is @stripe.com (or a subdomain like
#     @mail.stripe.com) and the user told us "stripe.com".
#
#  2. Hiring platform (ATS) — many companies email through
#     Greenhouse, Lever, Workday, etc., so the sender is e.g.
#     no-reply@us.greenhouse-mail.io. Then we require the company
#     name to appear as a WHOLE WORD in the sender name, the
#     address's local part ("stripe@myworkday.com"), or subject.
#
#  3. No domain given — accept if the sender's domain IS the
#     company name ("Acme Corp" ↔ acme.com) or the display name
#     contains it.
#
# Whole-word matters: a plain substring check would match "Meta"
# inside "metadata" or "Box" inside "Inbox".
# ============================================================

import re
from typing import Iterable, List, Optional

# Applicant-tracking systems that send mail on behalf of companies
ATS_DOMAINS = [
    "greenhouse.io", "greenhouse-mail.io",       # us./eu.greenhouse-mail.io
    "lever.co",                                   # hire.lever.co
    "ashbyhq.com",
    "myworkday.com", "workday.com",
    "smartrecruiters.com", "icims.com",
    "workablemail.com", "workable.com",
    "jobvite.com", "taleo.net", "successfactors.com",
    "bamboohr.com", "recruitee.com", "breezy.hr", "applytojob.com",
]

# Legal suffixes to ignore when comparing company names
_SUFFIXES = re.compile(r"\b(inc|llc|ltd|corp|corporation|co|company|plc|gmbh|group|holdings)\b\.?", re.I)


def domain_of(address: Optional[str]) -> str:
    return (address or "").rsplit("@", 1)[-1].lower()


def domain_matches(sender_domain: str, domain: str) -> bool:
    # exact, or a subdomain: mail.stripe.com matches stripe.com,
    # but notstripe.com does NOT (that's why we check ".stripe.com")
    return sender_domain == domain or sender_domain.endswith("." + domain)


def is_ats(sender_domain: str) -> bool:
    return any(domain_matches(sender_domain, d) for d in ATS_DOMAINS)


def normalize_company(name: str) -> str:
    name = _SUFFIXES.sub(" ", name.lower())
    name = re.sub(r"[^a-z0-9& ]+", " ", name)
    return " ".join(name.split())


def _name_in(name: str, haystack: str) -> bool:
    if not name:
        return False
    return re.search(rf"(?<![a-z0-9]){re.escape(name)}(?![a-z0-9])", haystack) is not None


def matches(app, msg: dict) -> bool:
    """app: Application row. msg: dict from gmail_client.get_message_meta."""
    sender = domain_of(msg.get("from_address"))
    if not sender:
        return False

    company = normalize_company(app.company_name)
    compact = company.replace(" ", "")
    local_part = (msg.get("from_address") or "").split("@")[0].replace(".", " ").replace("-", " ").replace("_", " ")
    haystack = normalize_company(" ".join([msg.get("from_name") or "", local_part, msg.get("subject") or ""]))

    # 1. Explicit company domain
    if app.company_domain and domain_matches(sender, app.company_domain):
        return True

    # 2. Hiring platform on the company's behalf
    if is_ats(sender):
        return _name_in(company, haystack) or (len(compact) > 3 and _name_in(compact, haystack))

    # 3. No domain given: sender domain looks like the company name
    if not app.company_domain:
        sld = sender.split(".")[-2] if sender.count(".") >= 1 else sender   # "acme" in mail.acme.com
        if compact and sld == compact:
            return True
        return _name_in(company, normalize_company(msg.get("from_name") or ""))

    return False


def pick_application(apps: Iterable, msg: dict):
    """Return (application, ambiguous) for the best match, or (None, False).
    If several applications match (two roles at one company), attach
    to the most recently applied one and flag it as ambiguous."""
    found: List = [a for a in apps if matches(a, msg)]
    if not found:
        return None, False
    found.sort(key=lambda a: a.applied_at or a.date_applied, reverse=True)
    return found[0], len(found) > 1


def gmail_query_terms(app) -> List[str]:
    """Search terms for Gmail's from:(...) operator for one application."""
    if app.company_domain:
        return [app.company_domain]
    name = normalize_company(app.company_name)
    return [f'"{name}"'] if name else []
