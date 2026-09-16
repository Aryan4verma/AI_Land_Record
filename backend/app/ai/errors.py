"""Classified provider failures.

`transient=True` means a later fallback layer may retry another
provider/model (07 sections 8-9); terminal errors must NOT be retried
blindly. Messages are static strings — they never include credentials,
request URLs (which carry the key), or raw secrets.
"""


class ProviderError(Exception):
    code = "PROVIDER_ERROR"
    transient = False

    def __init__(self, provider: str, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.provider = provider
        self.message = message
        # Optional diagnostic facts (status codes, paths, redacted bodies).
        # NEVER put credentials, URLs with query strings, headers, or tokens here.
        self.details = details or {}


class ProviderNotConfiguredError(ProviderError):
    code = "PROVIDER_NOT_CONFIGURED"


class ProviderAuthError(ProviderError):
    code = "PROVIDER_AUTH_ERROR"


class ProviderBadRequestError(ProviderError):
    code = "PROVIDER_BAD_REQUEST"


class ProviderBadResponseError(ProviderError):
    code = "PROVIDER_BAD_RESPONSE"


class ProviderRateLimitError(ProviderError):
    code = "PROVIDER_RATE_LIMITED"
    transient = True


class ProviderTimeoutError(ProviderError):
    code = "PROVIDER_TIMEOUT"
    transient = True


class ProviderUnavailableError(ProviderError):
    code = "PROVIDER_UNAVAILABLE"
    transient = True
