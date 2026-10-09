from __future__ import annotations

from datetime import date

from frontend.pages.dashboard import _calendar, _local_date, _local_time


def test_utc_appointment_is_displayed_in_sao_paulo_time():
    assert _local_time("2026-10-20T17:30:00") == "14:30"
    assert _local_date("2026-10-20T02:00:00") == date(2026, 10, 19)


def test_calendar_renders_real_bookings_and_escapes_client_names():
    appointments = [{
        "scheduled_at": "2026-10-20T17:30:00",
        "client_id": 1,
        "status": "scheduled",
    }]
    content = _calendar(2026, 10, appointments, {1: "<script>alert(1)</script>"})
    assert "14:30" in content
    assert "&lt;script&gt;" in content
    assert "<script>" not in content
    assert 'class="bf-calendar"' in content


def test_calendar_empty_month_displays_dates():
    content = _calendar(2026, 10, [], {})
    assert "bf-day" in content
    assert "bf-event" not in content
