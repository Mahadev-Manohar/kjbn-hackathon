"""Typed domain errors.

The API layer maps each class to one HTTP status and one response shape, so
rules never need to know about HTTP. `code` is a stable machine-readable
identifier; `message` is safe to show to a user.
"""


class DomainError(Exception):
    """Base class for every error raised deliberately by business rules."""

    code = "domain_error"

    def __init__(self, message: str, *, code: str | None = None, **details: object) -> None:
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code
        self.details = details


class InvalidInputError(DomainError):
    """The input itself is malformed or out of range (maps to 422)."""

    code = "invalid_input"


class RuleViolationError(DomainError):
    """The input is well-formed but a business rule forbids it (maps to 422)."""

    code = "rule_violation"


class NotFoundError(DomainError):
    """A referenced entity does not exist (maps to 404)."""

    code = "not_found"


class ConflictError(DomainError):
    """The action conflicts with current state, e.g. an immutable payout (maps to 409)."""

    code = "conflict"
