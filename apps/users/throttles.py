from rest_framework.throttling import SimpleRateThrottle


class LoginAccountRateThrottle(SimpleRateThrottle):
    """Per-account login throttle, layered on top of the per-IP one — an
    attacker spread across many IPs would otherwise get unlimited password
    guesses at one specific account, since the IP-based throttle never
    connects requests that don't share an IP."""
    scope = "login_account"

    def get_cache_key(self, request, view):
        email = (request.data.get("email") or "").strip().lower()
        if not email:
            return None
        return self.cache_format % {"scope": self.scope, "ident": email}
