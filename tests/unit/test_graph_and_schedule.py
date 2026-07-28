from datetime import date

import pytest

from app.config import Settings, validate_settings
from app.errors import DomainError
from app.schemas import CalendarInput
from app.services import _solve_positions, session_dates


def test_session_dates_exclude_holidays_and_exam() -> None:
    calendar = CalendarInput(
        start_date=date(2026, 8, 3), end_date=date(2026, 8, 14), exam_date=date(2026, 8, 14),
        session_days=["MONDAY", "WEDNESDAY", "FRIDAY"], session_minutes=45, holidays=[date(2026, 8, 5)], revision_sessions=1,
    )
    assert session_dates(calendar) == [date(2026, 8, 3), date(2026, 8, 7), date(2026, 8, 10), date(2026, 8, 12)]


def test_solver_respects_prerequisites_and_locks() -> None:
    concepts = [
        {"id": "force", "difficulty": 2}, {"id": "momentum", "difficulty": 3}, {"id": "energy", "difficulty": 4},
    ]
    positions = _solve_positions(concepts, 3, [("force", "momentum"), ("momentum", "energy")], {"force": 0})
    assert positions == {"force": 0, "momentum": 1, "energy": 2}


def test_solver_reports_when_too_many_concepts() -> None:
    assert _solve_positions([{"id": "a", "difficulty": 1}, {"id": "b", "difficulty": 1}], 1, []) is None


def test_production_settings_require_a_real_secret() -> None:
    with pytest.raises(RuntimeError):
        validate_settings(Settings(environment="production", secret="short"))
