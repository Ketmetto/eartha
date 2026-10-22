"""
Spam guard for public, no-account forms (wishlist requests, shop orders).

The page embeds a signed page-load timestamp (make_form_token). A
submission is only accepted with a token that's genuine (so scripts can't
skip loading the page), at least MIN_FILL_SECONDS old (no human fills a
form that fast) and no older than MAX_AGE (a stale tab just needs a
refresh). Pair it with a hidden honeypot field and a scoped throttle.
"""
import time

from django.core import signing

MIN_FILL_SECONDS = 3
MAX_AGE = 60 * 60 * 24


class FormTokenExpired(Exception):
    pass


def make_form_token(salt):
    return signing.dumps(time.time(), salt=salt)


def check_form_token(token, salt):
    """Returns True if the form was filled at a human pace, False if it
    was submitted too fast (treat as a bot). Raises FormTokenExpired for
    a missing, forged or expired token."""
    try:
        issued_at = signing.loads(token, salt=salt, max_age=MAX_AGE)
    except signing.BadSignature:
        raise FormTokenExpired
    return time.time() - float(issued_at) >= MIN_FILL_SECONDS
