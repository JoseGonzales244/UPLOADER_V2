class DomainException(Exception):
    """Base exception for domain layer errors."""
    pass


class InvalidEmployeeDataException(DomainException):
    """Raised when employee invariants are violated."""
    pass


class InvalidAbsenceDataException(DomainException):
    """Raised when absence payload formatting or dates are invalid."""
    pass


class RepositoryException(Exception):
    """Base exception for persistence and adapter layer failures."""
    pass
