# Does an email belong to an application?
from datetime import datetime
from types import SimpleNamespace

from services.email_matching import matches, pick_application


def app(name, domain=None, applied=datetime(2026, 11, 1)):
    return SimpleNamespace(company_name=name, company_domain=domain, applied_at=applied, date_applied=applied)


def msg(address, name="", subject=""):
    return {"from_address": address, "from_name": name, "subject": subject}


def test_company_domain_and_subdomain():
    a = app("Stripe", "stripe.com")
    assert matches(a, msg("recruiting@stripe.com"))
    assert matches(a, msg("no-reply@mail.stripe.com"))


def test_lookalike_domain_does_not_match():
    a = app("Stripe", "stripe.com")
    assert not matches(a, msg("hr@notstripe.com"))
    assert not matches(a, msg("hr@stripe.com.evil.io"))


def test_ats_requires_company_name():
    a = app("Stripe", "stripe.com")
    assert matches(a, msg("no-reply@us.greenhouse-mail.io", "Stripe Recruiting"))
    assert matches(a, msg("no-reply@hire.lever.co", subject="Your application to Stripe"))
    assert not matches(a, msg("no-reply@us.greenhouse-mail.io", "Plaid Recruiting"))


def test_workday_local_part():
    a = app("Acme Corp")
    assert matches(a, msg("acme@myworkday.com", "Workday"))


def test_whole_word_only():
    meta = app("Meta")
    assert not matches(meta, msg("no-reply@greenhouse.io", subject="Your metadata export"))
    assert matches(meta, msg("no-reply@greenhouse.io", subject="Your application to Meta"))


def test_no_domain_falls_back_to_sender_domain():
    a = app("Acme, Inc.")
    assert matches(a, msg("jobs@acme.com"))
    assert not matches(a, msg("jobs@acmeco.com"))


def test_two_roles_same_company_is_ambiguous():
    older = app("Stripe", "stripe.com", datetime(2026, 10, 1))
    newer = app("Stripe", "stripe.com", datetime(2026, 11, 1))
    chosen, ambiguous = pick_application([older, newer], msg("hr@stripe.com"))
    assert chosen is newer and ambiguous is True
