# The classifier is pure logic, so we can pin down real-world
# examples — including the tricky ones the reviewer flagged.
import pytest

from services.classifier import classify


@pytest.mark.parametrize("subject,snippet,expected", [
    # Offers
    ("Your offer letter from Stripe", "", "offer"),
    ("Congratulations!", "We are pleased to offer you the Software Engineering Intern position", "offer"),
    # Rejections
    ("Your application to Acme", "Unfortunately, we have decided to move forward with other candidates.", "rejection"),
    ("Update on your application", "We regret to inform you that you were not selected", "rejection"),
    ("Thank you for your interest in Acme", "After careful consideration we will not be moving forward", "rejection"),
    # Interviews
    ("Interview invitation - Acme", "", "interview"),
    ("Next steps", "Please share your availability for a phone screen this week", "interview"),
    ("Acme coding challenge", "Complete the HackerRank assessment within 7 days", "interview"),
    # Acknowledgments
    ("Thank you for applying to Acme!", "We've received your application and will review it.", "acknowledgment"),
    # Plain other
    ("Acme newsletter", "Read our latest engineering blog posts", "other"),
])
def test_examples(subject, snippet, expected):
    assert classify(subject, snippet)[0] == expected


def test_interview_word_alone_is_not_an_offer():
    # "offer you an interview" must NOT be read as a job offer
    assert classify("We'd like to offer you an interview", "Please book a time")[0] == "interview"


def test_unfortunately_alone_is_not_a_rejection():
    # weak signal only — the interviewer is rescheduling, not rejecting
    label, _ = classify("Interview reschedule", "Unfortunately the interviewer is out sick, can we pick a new time?")
    assert label != "rejection"


def test_acknowledgment_with_next_steps_is_not_an_interview():
    label, _ = classify("Thanks for applying", "Next steps: our team will reach out if we'd like to interview you.")
    assert label == "acknowledgment"


def test_rejection_after_interview_wins():
    label, suggested = classify("Following up on your interview",
                                "Thank you for interviewing. Unfortunately we decided to move forward with other candidates.")
    assert label == "rejection"
    assert suggested == "Rejected"


def test_curly_apostrophes():
    assert classify("Update", "Unfortunately we won’t be moving forward with your application")[0] == "rejection"
