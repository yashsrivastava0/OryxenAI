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


class AdminSelfActionForbiddenError(AuthError):
    code = "ADMIN_SELF_ACTION_FORBIDDEN"
    status_code = 409

    def __init__(self) -> None:
        super().__init__("Administrators cannot perform this action on their own identity.")


class LastActiveAdminRequiredError(AuthError):
    code = "LAST_ACTIVE_ADMIN_REQUIRED"
    status_code = 409

    def __init__(self) -> None:
        super().__init__("At least one active administrator must remain.")


class AdminConfirmationMismatchError(AuthError):
    code = "ADMIN_CONFIRMATION_MISMATCH"
    status_code = 409

    def __init__(self) -> None:
        super().__init__("The destructive-action confirmation does not match the target.")


class AdminIdempotencyRequiredError(AuthError):
    code = "ADMIN_IDEMPOTENCY_REQUIRED"
    status_code = 400

    def __init__(self) -> None:
        super().__init__("A bounded Idempotency-Key is required for administrator mutations.")


class AdminOperationConflictError(AuthError):
    code = "ADMIN_OPERATION_CONFLICT"
    status_code = 409

    def __init__(self) -> None:
        super().__init__("That administrator operation key was used with different input.")


class AdminOperationRetryableError(AuthError):
    code = "ADMIN_OPERATION_RETRYABLE"
    status_code = 503

    def __init__(self) -> None:
        super().__init__("The administrator operation needs a safe retry.", retryable=True)


class AdminProviderUnavailableError(AuthError):
    code = "AUTH_ADMIN_PROVIDER_UNAVAILABLE"
    status_code = 503

    def __init__(self) -> None:
        super().__init__(
            "The identity provider administrator operation is temporarily unavailable.",
            retryable=True,
        )


class AdminProviderRateLimitedError(AuthError):
    code = "AUTH_ADMIN_PROVIDER_RATE_LIMITED"
    status_code = 429

    def __init__(self) -> None:
        super().__init__("The identity provider administrator operation is rate limited.")


class ProjectDeletionPendingError(AuthError):
    code = "PROJECT_DELETION_PENDING"
    status_code = 409

    def __init__(self) -> None:
        super().__init__("This portfolio is being deleted and cannot accept new work.")


class ProjectRunningWorkPendingError(AuthError):
    code = "PROJECT_RUNNING_WORK_PENDING"
    status_code = 409

    def __init__(self) -> None:
        super().__init__("Running portfolio work must finish before cleanup can continue.")


class ProjectMustBeDeletedBeforeEntitlementResetError(AuthError):
    code = "PROJECT_MUST_BE_DELETED_BEFORE_ENTITLEMENT_RESET"
    status_code = 409

    def __init__(self) -> None:
        super().__init__("Delete the current portfolio before resetting its entitlement.")


class EntitlementResetNotApplicableError(AuthError):
    code = "ENTITLEMENT_RESET_NOT_APPLICABLE"
    status_code = 409

    def __init__(self) -> None:
        super().__init__("This entitlement has no deleted portfolio to reset.")


class AdminDemotionRequiresProjectCleanupError(AuthError):
    code = "ADMIN_DEMOTION_REQUIRES_PROJECT_CLEANUP"
    status_code = 409

    def __init__(self) -> None:
        super().__init__("An administrator must have no live portfolio before demotion.")


class DeletedIdentityNotReadmittableError(AuthError):
    code = "DELETED_IDENTITY_NOT_READMITTABLE"
    status_code = 409

    def __init__(self) -> None:
        super().__init__("This identity tombstone is not ready for readmission.")


class StorageCleanupFailedError(AuthError):
    code = "STORAGE_CLEANUP_FAILED"
    status_code = 503

    def __init__(self) -> None:
        super().__init__("The portfolio storage cleanup needs a safe retry.", retryable=True)


class GenerationVariantLockedError(AuthError):
    code = "GENERATION_VARIANT_LOCKED"
    status_code = 409

    def __init__(self) -> None:
        super().__init__(
            "This account already has its one Code Generator variant. Retry the existing run."
        )


class PortfolioReadOnlyError(AuthError):
    code = "PORTFOLIO_READ_ONLY"
    status_code = 409

    def __init__(self) -> None:
        super().__init__("This portfolio has a promoted success and is now read-only.")


class EntitlementBindingConflictError(AuthError):
    code = "ENTITLEMENT_BINDING_CONFLICT"
    status_code = 409

    def __init__(self) -> None:
        super().__init__(
            "The portfolio authorization binding is inconsistent and cannot be changed safely."
        )


class AuthorizationFenceRejectedError(AuthError):
    code = "AUTHORIZATION_FENCE_REJECTED"
    status_code = 409

    def __init__(self) -> None:
        super().__init__("This background operation is no longer authorized to continue.")


class ModelProviderCreditExhaustedError(AuthError):
    code = "MODEL_PROVIDER_CREDIT_EXHAUSTED"
    status_code = 503

    def __init__(self) -> None:
        super().__init__(
            "The configured model provider has no available credit. Retry this same run later.",
            retryable=False,
        )
