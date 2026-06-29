"""Tests for laraflask.scheduler - ScheduledEvent and Schedule."""

import datetime
import pytest

from laraflask.scheduler.scheduled_event import ScheduledEvent
from laraflask.scheduler._schedule import Schedule


class TestScheduledEventFrequency:
    """Test frequency helper methods set correct cron expressions."""

    def test_every_minute(self):
        event = ScheduledEvent(lambda: None).every_minute()
        assert event._expression == "* * * * *"

    def test_every_five_minutes(self):
        event = ScheduledEvent(lambda: None).every_five_minutes()
        assert event._expression == "*/5 * * * *"

    def test_every_ten_minutes(self):
        event = ScheduledEvent(lambda: None).every_ten_minutes()
        assert event._expression == "*/10 * * * *"

    def test_every_fifteen_minutes(self):
        event = ScheduledEvent(lambda: None).every_fifteen_minutes()
        assert event._expression == "*/15 * * * *"

    def test_every_thirty_minutes(self):
        event = ScheduledEvent(lambda: None).every_thirty_minutes()
        assert event._expression == "*/30 * * * *"

    def test_hourly(self):
        event = ScheduledEvent(lambda: None).hourly()
        assert event._expression == "0 * * * *"

    def test_hourly_at(self):
        event = ScheduledEvent(lambda: None).hourly_at(15)
        assert event._expression == "15 * * * *"

    def test_daily(self):
        event = ScheduledEvent(lambda: None).daily()
        assert event._expression == "0 0 * * *"

    def test_daily_at(self):
        event = ScheduledEvent(lambda: None).daily_at("13:30")
        assert event._expression == "30 13 * * *"

    def test_weekly(self):
        event = ScheduledEvent(lambda: None).weekly()
        assert event._expression == "0 0 * * 0"

    def test_monthly(self):
        event = ScheduledEvent(lambda: None).monthly()
        assert event._expression == "0 0 1 * *"

    def test_quarterly(self):
        event = ScheduledEvent(lambda: None).quarterly()
        assert event._expression == "0 0 1 1,4,7,10 *"

    def test_yearly(self):
        event = ScheduledEvent(lambda: None).yearly()
        assert event._expression == "0 0 1 1 *"

    def test_twice_daily(self):
        event = ScheduledEvent(lambda: None).twice_daily(8, 20)
        assert event._expression == "0 8,20 * * *"


class TestScheduledEventDayConstraints:
    """Test day-of-week constraints."""

    def test_weekdays(self):
        event = ScheduledEvent(lambda: None).daily().weekdays()
        assert event._expression == "0 0 * * 1-5"

    def test_weekends(self):
        event = ScheduledEvent(lambda: None).daily().weekends()
        assert event._expression == "0 0 * * 0,6"

    def test_mondays(self):
        event = ScheduledEvent(lambda: None).daily().mondays()
        assert event._expression == "0 0 * * 1"

    def test_fridays(self):
        event = ScheduledEvent(lambda: None).daily().fridays()
        assert event._expression == "0 0 * * 5"


class TestScheduledEventIsDue:
    """Test is_due() cron matching (uses built-in _field_match when croniter is unavailable)."""

    def test_every_minute_always_due(self):
        event = ScheduledEvent(lambda: None).every_minute()
        now = datetime.datetime(2024, 6, 15, 10, 30)
        assert event.is_due(now) is True

    def test_hourly_at_zero(self):
        event = ScheduledEvent(lambda: None).hourly()
        # Minute 0 should match
        assert event.is_due(datetime.datetime(2024, 6, 15, 10, 0)) is True
        # Minute 30 should not match
        assert event.is_due(datetime.datetime(2024, 6, 15, 10, 30)) is False

    def test_daily_at_midnight(self):
        event = ScheduledEvent(lambda: None).daily()
        assert event.is_due(datetime.datetime(2024, 6, 15, 0, 0)) is True
        assert event.is_due(datetime.datetime(2024, 6, 15, 12, 0)) is False

    def test_custom_cron(self):
        # Every day at 9:00
        event = ScheduledEvent(lambda: None).cron("0 9 * * *")
        assert event.is_due(datetime.datetime(2024, 6, 15, 9, 0)) is True
        assert event.is_due(datetime.datetime(2024, 6, 15, 10, 0)) is False

    def test_every_five_minutes_matching(self):
        event = ScheduledEvent(lambda: None).every_five_minutes()
        # Minute 0 matches */5
        assert event.is_due(datetime.datetime(2024, 6, 15, 10, 0)) is True
        # Minute 15 matches */5
        assert event.is_due(datetime.datetime(2024, 6, 15, 10, 15)) is True
        # Minute 7 does not match */5
        assert event.is_due(datetime.datetime(2024, 6, 15, 10, 7)) is False


class TestScheduledEventConditions:
    """Test when/skip conditions."""

    def test_when_condition_passes(self):
        event = ScheduledEvent(lambda: None).every_minute()
        event.when(lambda: True)
        assert event.is_due(datetime.datetime(2024, 6, 15, 10, 0)) is True

    def test_when_condition_fails(self):
        event = ScheduledEvent(lambda: None).every_minute()
        event.when(lambda: False)
        assert event.is_due(datetime.datetime(2024, 6, 15, 10, 0)) is False

    def test_skip_condition_rejects(self):
        event = ScheduledEvent(lambda: None).every_minute()
        event.skip(lambda: True)
        assert event.is_due(datetime.datetime(2024, 6, 15, 10, 0)) is False

    def test_skip_condition_allows(self):
        event = ScheduledEvent(lambda: None).every_minute()
        event.skip(lambda: False)
        assert event.is_due(datetime.datetime(2024, 6, 15, 10, 0)) is True

    def test_environments_filter(self):
        import os
        os.environ["APP_ENV"] = "testing"
        event = ScheduledEvent(lambda: None).every_minute()
        event.environments("production")
        assert event.is_due() is False
        # Restore
        os.environ.pop("APP_ENV", None)


class TestScheduledEventRun:
    """Test event execution."""

    def test_run_calls_callback(self):
        results = []
        event = ScheduledEvent(lambda: results.append("executed"))
        event.run()
        assert results == ["executed"]

    def test_before_and_after_hooks(self):
        order = []
        event = ScheduledEvent(lambda: order.append("main"))
        event.before(lambda: order.append("before"))
        event.after(lambda: order.append("after"))
        event.run()
        assert order == ["before", "main", "after"]


class TestScheduledEventOptions:
    """Test various option setters."""

    def test_description(self):
        event = ScheduledEvent(lambda: None).description("Clean cache")
        assert event._description == "Clean cache"

    def test_without_overlapping(self):
        event = ScheduledEvent(lambda: None).without_overlapping()
        assert event._without_overlapping is True

    def test_run_in_background(self):
        event = ScheduledEvent(lambda: None).run_in_background()
        assert event._run_in_background is True

    def test_timezone(self):
        event = ScheduledEvent(lambda: None).timezone("America/New_York")
        assert event._timezone == "America/New_York"

    def test_summary(self):
        event = ScheduledEvent(lambda: None, "my task").daily()
        assert "0 0 * * *" in event.summary()
        assert "my task" in event.summary()


class TestScheduleFacade:
    """Test the Schedule class-level methods."""

    def setup_method(self):
        # Clear scheduled events between tests
        Schedule._events = []

    def test_call_registers_event(self):
        event = Schedule.call(lambda: "hello", "test task")
        assert event in Schedule.get_events()
        assert isinstance(event, ScheduledEvent)

    def test_get_events(self):
        Schedule.call(lambda: None, "task 1")
        Schedule.call(lambda: None, "task 2")
        assert len(Schedule.get_events()) == 2

    def test_due_events(self):
        # Every minute should always be due
        Schedule.call(lambda: None, "always").every_minute()
        # Yearly at specific time - likely not due right now
        Schedule.call(lambda: None, "rare").yearly()

        now = datetime.datetime(2024, 6, 15, 10, 30)
        due = Schedule.due_events(now)
        # The every_minute task should be due
        assert any(e._description == "always" for e in due)

    def test_run_due_executes(self):
        results = []
        Schedule.call(lambda: results.append("ran"), "runner").every_minute()
        count = Schedule.run_due()
        assert count >= 1
        assert "ran" in results

    def test_list_returns_summaries(self):
        Schedule.call(lambda: None, "summary task").daily()
        summaries = Schedule.list()
        assert len(summaries) == 1
        assert "summary task" in summaries[0]
