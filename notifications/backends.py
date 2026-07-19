"""
Provider adapters. Keep email/SMS provider specifics here so swapping
providers later doesn't touch task or service code elsewhere.
"""


class EmailBackend:
    def send(self, to: str, subject: str, body: str):
        raise NotImplementedError


class SMSBackend:
    def send(self, to: str, body: str):
        raise NotImplementedError
