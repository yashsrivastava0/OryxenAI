"""Safe authentication errors mapped to the existing API envelope."""

from __future__ import annotations

from oryxenai.api.errors import AppError


class AuthError(AppError):
    """Base class for errors safe to expose at the auth boundary."""


class AuthRequiredError(AuthError):
    code = "AUTH_REQUIRED"
    status_code = 401

    def __init__(self) -> None:
        super().__init__("Authentication is required.")


class AuthInvalidError(AuthError):
    code = "AUTH_INVALID"
    status_code = 401

    def __init__(self) -> None:
        super().__init__("The authentication session is invalid or expired.")


class AuthProviderUnavailableError(AuthError):
    code = "AUTH_PROVIDER_UNAVAILABLE"
    status_code = 503

    def __init__(self) -> None:
        super().__init__(
            "Authentication is temporarily unavailable. Please try again shortly.",
            retryable=True,
        )


class AuthRateLimitedError(AuthError):
    code = "AUTH_RATE_LIMITED"
    status_code = 429

    def __init__(self) -> None:
        super().__init__("Authentication is temporarily rate limited. Please try again shortly.")


class AccessNotApprovedError(AuthError):
    code = "ACCESS_NOT_APPROVED"
    status_code = 403

    def __init__(self) -> None:
        super().__init__("This Google account is not approved for OryxenAI access.")


class AccountSuspendedError(AuthError):
    code = "ACCOUNT_SUSPENDED"
    status_code = 403

    def __init__(self) -> None:
        super().__init__("This OryxenAI account is currently unavailable.")


class AccountDeletedError(AuthError):
    code = "ACCOUNT_DELETED"
    status_code = 403

    def __init__(self) -> None:
        super().__init__("This OryxenAI account is no longer available.")


class AdminRequiredError(AuthError):
    code = "ADMIN_REQUIRED"
    status_code = 403

    def __init__(self) -> None:
        super().__init__("Administrator access is required.")


class OnboardingRequiredError(AuthError):
    code = "ONBOARDING_REQUIRED"
    status_code = 403

    def __init__(self) -> None:
        super().__init__("Complete username onboarding before using this page.")


class UsernameTakenError(AuthError):
    code = "USERNAME_TAKEN"
    status_code = 409

    def __init__(self) -> None:
        super().__init__("That username is already taken.")


class UsernameLockedError(AuthError):
    code = "USERNAME_LOCKED"
    status_code = 409

    def __init__(self) -> None:
        super().__init__("Your username cannot be changed after onboarding.")


class UserCapacityReachedError(AuthError):
    code = "USER_CAPACITY_REACHED"
    status_code = 409

    def __init__(self) -> None:
        super().__init__("Normal-user access is currently at capacity.")
