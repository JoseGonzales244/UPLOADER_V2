from typing import Protocol, List, Optional
from modules.dotacion.domain.entities.employee import Employee
from modules.dotacion.domain.entities.absence import AbsenceRecord


class WorkforceRepository(Protocol):
    """Abstract Port for accessing and persisting Workforce (Dotación) data."""

    def load_employees(self) -> List[Employee]:
        ...

    def save_employees(self, employees: List[Employee]) -> None:
        ...


class AbsenceRepository(Protocol):
    """Abstract Port for loading and persisting Absence/Vacation data."""

    def load_absences(self) -> List[AbsenceRecord]:
        ...

    def get_absence_by_employee_code(self, code: str) -> Optional[AbsenceRecord]:
        ...
