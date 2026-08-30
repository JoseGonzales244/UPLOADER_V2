import datetime
from dataclasses import dataclass, field
from typing import List, Tuple, Optional


@dataclass(frozen=True)
class VacationPeriod:
    start_date: datetime.date
    end_date: datetime.date

    def __post_init__(self):
        if self.start_date > self.end_date:
            raise ValueError(f"Start date {self.start_date} cannot be after end date {self.end_date}")

    def contains(self, check_date: datetime.date) -> bool:
        return self.start_date <= check_date <= self.end_date


@dataclass
class AbsenceRecord:
    employee_code: str
    total_absence_days: int = 0
    total_vacation_days: int = 0
    situation: str = ""
    vacation_periods: List[VacationPeriod] = field(default_factory=list)

    def evaluate_status(
        self,
        num_business_days: int,
        holidays_set: set,
        year: int,
        month: int
    ) -> Optional[str]:
        """
        Evalúa el estado de ausentismo del ejecutivo según reglas de negocio (VACACIONES, LICENCIA, etc).
        """
        situacion_upper = str(self.situation).strip().upper()
        if situacion_upper != 'CON AUSENCIA':
            return None

        # El último día hábil no se cuenta para evaluación
        eval_business_days = num_business_days - 1

        # Encontrar último día hábil
        last_b_day = self._get_last_business_day(year, month, holidays_set)

        # Verificar si alguna vacación del ejecutivo incluye el último día hábil
        is_vac_on_last_day = any(vp.contains(last_b_day) for vp in self.vacation_periods)

        # Ajustar días de vacaciones para periodo de evaluación
        eval_vac_days = self.total_vacation_days - 1 if is_vac_on_last_day else self.total_vacation_days
        vac_ratio = (eval_vac_days / eval_business_days) if eval_business_days > 0 else 0

        # Regla 1: Vacaciones cubren el 95% o más del mes hábil
        if round(vac_ratio, 2) >= 0.95 or self.total_vacation_days >= num_business_days:
            return 'VACACIONES TODO EL MES'
        elif self.total_vacation_days >= 5 or vac_ratio >= 0.25:
            return 'VACACIONES'

        # Regla 2: Total ausente por licencias
        if self.total_absence_days >= num_business_days:
            return 'LICENCIA'

        # Regla 3: Licencias médicas u otras ausencias no vacaciones que cubren casi todo el mes
        non_vac_absence = self.total_absence_days - self.total_vacation_days
        if non_vac_absence >= num_business_days - 2:
            return 'LICENCIA'

        return None

    @staticmethod
    def _get_last_business_day(year: int, month: int, holidays_set: set) -> datetime.date:
        if month == 12:
            last_day = datetime.date(year, 12, 31)
        else:
            last_day = datetime.date(year, month + 1, 1) - datetime.timedelta(days=1)

        curr_date = last_day
        while curr_date.month == month:
            if curr_date.weekday() < 5 and curr_date not in holidays_set:
                return curr_date
            curr_date -= datetime.timedelta(days=1)
        return last_day
