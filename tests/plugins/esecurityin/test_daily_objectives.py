#!/usr/bin/env python
# -*- coding: utf-8 -*-
import threading
from datetime import date

import pytest
from freezegun import freeze_time
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from CTFd.models import Users
from tests.helpers import (
    create_ctfd,
    destroy_ctfd,
    gen_challenge,
    gen_flag,
    gen_solve,
    gen_user,
    login_as_user,
    register_user,
)

ACTIVE_OBJECTIVE_KEYS = ["daily_first_breach", "daily_operator", "daily_xp_hunter"]
TODAY = date(2026, 10, 21)

# The eSecurityIn package cannot be imported at module scope because importing
# it requires an app context. _load_esecurityin() binds these names once the
# plugin-enabled app fixture has created an app.
DailyObjective = None
UserDailyObjective = None
DailyObjectiveService = None
UserXP = None


def _load_esecurityin():
    """Import and bind the eSecurityIn classes for use by all tests."""
    global DailyObjective, UserDailyObjective, DailyObjectiveService, UserXP
    from CTFd.plugins.esecurityin.models import (
        DailyObjective,
        UserDailyObjective,
        UserXP,
    )
    from CTFd.plugins.esecurityin.services.daily_objective_service import (
        DailyObjectiveService,
    )


@pytest.fixture
def app():
    """
    Create a plugin-enabled CTFd app and guarantee its isolated DB is dropped.

    The database is removed in teardown even when a test fails or is skipped
    after the app has been created.
    """
    app = create_ctfd(enable_plugins=True)
    try:
        with app.app_context():
            _load_esecurityin()
        yield app
    finally:
        destroy_ctfd(app)


def _require_mysql(app):
    """
    Skip tests that depend on MariaDB/MySQL-specific SQL.

    ``DailyObjectiveService.process_solve`` uses ``INSERT ... ON DUPLICATE KEY
    UPDATE``, ``SELECT ... FOR UPDATE`` and ``CURRENT_TIMESTAMP(6)`` which are
    not valid SQLite or PostgreSQL.
    """
    uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
    if not (uri.startswith("mysql") or uri.startswith("mariadb")):
        pytest.skip(
            "Daily objective tests require a MySQL/MariaDB backend "
            "(TESTING_DATABASE_URL)"
        )


# ---------------------------------------------------------------------------
# Always-run tests (work on any backend, including the default SQLite config)
# ---------------------------------------------------------------------------


def test_seed_objectives_is_idempotent(app):
    """Seeding the default objectives must never create duplicate definitions."""
    with app.app_context():
        DailyObjectiveService.seed_objectives()
        DailyObjectiveService.seed_objectives()

        objectives = DailyObjective.query.order_by(DailyObjective.id.asc()).all()

        assert [objective.key for objective in objectives] == ACTIVE_OBJECTIVE_KEYS
        assert DailyObjective.query.count() == len(ACTIVE_OBJECTIVE_KEYS)


def test_get_or_create_daily_progress_returns_same_row(app):
    """Getting today's progress twice must return the same single row."""
    with app.app_context():
        user = gen_user(app.db)
        objective = DailyObjective.query.first()
        app.db.session.commit()

        with freeze_time(TODAY):
            first = DailyObjectiveService.get_or_create_daily_progress(
                user.id, objective
            )
            app.db.session.commit()
            second = DailyObjectiveService.get_or_create_daily_progress(
                user.id, objective
            )

            assert second is first
            assert first.progress == 0
            assert first.completed is False
            assert UserDailyObjective.query.count() == 1
def test_unique_constraint_blocks_duplicate_progress_row(app):
    """The (user_id, objective_id, objective_date) constraint must be enforced."""
    with app.app_context():
        user = gen_user(app.db)
        objective = DailyObjective.query.first()
        app.db.session.commit()

        with freeze_time(TODAY):
            DailyObjectiveService.get_or_create_daily_progress(user.id, objective)
            app.db.session.commit()

            duplicate = UserDailyObjective(
                user_id=user.id,
                objective_id=objective.id,
                objective_date=TODAY,
                progress=0,
                completed=False,
            )
            app.db.session.add(duplicate)
            with pytest.raises(IntegrityError):
                app.db.session.commit()
            app.db.session.rollback()

            assert UserDailyObjective.query.count() == 1


def test_get_or_create_daily_progress_is_per_day(app):
    """A different calendar day must produce a separate progress row."""
    with app.app_context():
        user = gen_user(app.db)
        objective = DailyObjective.query.first()
        app.db.session.commit()

        with freeze_time(date(2026, 10, 20)):
            day_one = DailyObjectiveService.get_or_create_daily_progress(
                user.id, objective
            )
        app.db.session.commit()
        with freeze_time(TODAY):
            day_two = DailyObjectiveService.get_or_create_daily_progress(
                user.id, objective
            )

        assert day_one.objective_date == date(2026, 10, 20)
        assert day_two.objective_date == TODAY
        assert day_one is not day_two
        assert UserDailyObjective.query.count() == 2


def test_get_today_returns_active_objectives_with_progress(app):
    """get_today must report all active objectives and their current progress."""
    with app.app_context():
        user = gen_user(app.db)
        app.db.session.commit()

        with freeze_time(TODAY):
            items = DailyObjectiveService.get_today(user.id)

            assert [item["key"] for item in items] == ACTIVE_OBJECTIVE_KEYS
            for item in items:
                assert item["progress"] == 0
                assert item["completed"] is False
                assert item["remaining"] == item["target_value"]

            objective = DailyObjective.query.filter_by(
                key="daily_operator"
            ).first()
            progress = DailyObjectiveService.get_or_create_daily_progress(
                user.id, objective
            )
            progress.progress = 2
            app.db.session.commit()

            items = DailyObjectiveService.get_today(user.id)
            operator = next(
                item for item in items if item["key"] == "daily_operator"
            )
            assert operator["progress"] == 2
            assert operator["remaining"] == 1
            assert operator["completed"] is False

# ---------------------------------------------------------------------------
# MySQL/MariaDB-only tests (skip on SQLite and PostgreSQL)
# ---------------------------------------------------------------------------


def test_process_solve_increments_daily_solves_per_solve(app):
    """Each successful solve must increase daily_solves progress by exactly one."""
    _require_mysql(app)
    with app.app_context():
        user = gen_user(app.db)
        operator = DailyObjective.query.filter_by(key="daily_operator").first()
        breach = DailyObjective.query.filter_by(key="daily_first_breach").first()
        app.db.session.commit()

        with freeze_time(TODAY):
            completed = DailyObjectiveService.process_solve(
                app.db.session, user.id, challenge_xp=1
            )
            app.db.session.commit()
            assert [c["key"] for c in completed] == ["daily_first_breach"]

            completed = DailyObjectiveService.process_solve(
                app.db.session, user.id, challenge_xp=1
            )
            app.db.session.commit()
            assert completed == []

            completed = DailyObjectiveService.process_solve(
                app.db.session, user.id, challenge_xp=1
            )
            app.db.session.commit()
            assert [c["key"] for c in completed] == ["daily_operator"]

            operator_rows = UserDailyObjective.query.filter_by(
                user_id=user.id, objective_id=operator.id
            ).all()
            assert len(operator_rows) == 1
            assert operator_rows[0].progress == 3
            assert operator_rows[0].completed is True

            breach_rows = UserDailyObjective.query.filter_by(
                user_id=user.id, objective_id=breach.id
            ).all()
            assert len(breach_rows) == 1
            assert breach_rows[0].progress == 1
            assert breach_rows[0].completed is True


def test_process_solve_daily_xp_accumulates_and_caps_at_target(app):
    """daily_xp progress must accumulate challenge XP and cap at target_value."""
    _require_mysql(app)
    with app.app_context():
        user = gen_user(app.db)
        hunter = DailyObjective.query.filter_by(key="daily_xp_hunter").first()
        app.db.session.commit()

        with freeze_time(TODAY):
            completed = DailyObjectiveService.process_solve(
                app.db.session, user.id, challenge_xp=60
            )
            app.db.session.commit()
            assert [c["key"] for c in completed] == ["daily_first_breach"]

            completed = DailyObjectiveService.process_solve(
                app.db.session, user.id, challenge_xp=50
            )
            app.db.session.commit()
            assert [c["key"] for c in completed] == ["daily_xp_hunter"]
            hunter_completed = next(
                c for c in completed if c["key"] == "daily_xp_hunter"
            )
            assert hunter_completed["progress"] == 100

            hunter_rows = UserDailyObjective.query.filter_by(
                user_id=user.id, objective_id=hunter.id
            ).all()
            assert len(hunter_rows) == 1
            assert hunter_rows[0].progress == 100
            assert hunter_rows[0].completed is True

def test_completed_objective_is_not_completed_or_rewarded_again(app):
    """An already completed objective must never be completed or rewarded again."""
    _require_mysql(app)
    with app.app_context():
        user = gen_user(app.db)
        breach = DailyObjective.query.filter_by(key="daily_first_breach").first()
        app.db.session.commit()

        with freeze_time(TODAY):
            completed = DailyObjectiveService.process_solve(
                app.db.session, user.id, challenge_xp=1
            )
            app.db.session.commit()
            assert [c["key"] for c in completed] == ["daily_first_breach"]

            breach_row = UserDailyObjective.query.filter_by(
                user_id=user.id, objective_id=breach.id
            ).first()
            assert breach_row.progress == 1
            assert breach_row.completed is True
            completed_at = breach_row.completed_at
            assert completed_at is not None

            # Repeated solves on the same day must not re-complete or re-reward.
            for _ in range(3):
                completed = DailyObjectiveService.process_solve(
                    app.db.session, user.id, challenge_xp=1
                )
                app.db.session.commit()
                assert "daily_first_breach" not in [
                    objective["key"] for objective in completed
                ]

            breach_row = UserDailyObjective.query.filter_by(
                user_id=user.id, objective_id=breach.id
            ).first()
            assert breach_row.progress == 1
            assert breach_row.completed is True
            assert breach_row.completed_at == completed_at


def test_process_solve_keeps_one_progress_row_per_day(app):
    """Repeated solves must never create more than one row per objective per day."""
    _require_mysql(app)
    with app.app_context():
        user = gen_user(app.db)
        app.db.session.commit()

        with freeze_time(TODAY):
            DailyObjectiveService.process_solve(
                app.db.session, user.id, challenge_xp=1
            )
            app.db.session.commit()
            DailyObjectiveService.process_solve(
                app.db.session, user.id, challenge_xp=1
            )
            app.db.session.commit()

            rows = UserDailyObjective.query.filter_by(user_id=user.id).all()
            assert len(rows) == len(ACTIVE_OBJECTIVE_KEYS)

            for objective in DailyObjective.query.all():
                count = UserDailyObjective.query.filter_by(
                    user_id=user.id, objective_id=objective.id
                ).count()
                assert count == 1


def test_concurrent_process_solve_initializes_single_progress_row(app):
    """Concurrent solves must produce one shared progress row with full progress."""
    _require_mysql(app)
    with app.app_context():
        user = gen_user(app.db)
        user_id = user.id
        operator = DailyObjective.query.filter_by(key="daily_operator").first()
        app.db.session.commit()

        session_factory = sessionmaker(bind=app.db.engine)
        barrier = threading.Barrier(2)
        errors = []
        lock = threading.Lock()

        def worker():
            session = session_factory()
            try:
                barrier.wait(timeout=10)
                DailyObjectiveService.process_solve(
                    session=session, user_id=user_id, challenge_xp=1
                )
                session.commit()
            except Exception as exc:  # pragma: no cover - surfaced by assertion
                with lock:
                    errors.append(exc)
                session.rollback()
            finally:
                session.close()

        with freeze_time(TODAY):
            threads = [threading.Thread(target=worker) for _ in range(2)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=30)

        assert not any(thread.is_alive() for thread in threads)
        assert errors == []

        # End the main transaction so subsequent reads see committed worker data.
        app.db.session.rollback()
        rows = UserDailyObjective.query.filter_by(
            user_id=user_id, objective_id=operator.id
        ).all()
        assert len(rows) == 1
        assert rows[0].progress == 2
        assert rows[0].completed is False
        assert UserDailyObjective.query.count() == len(ACTIVE_OBJECTIVE_KEYS)


def test_solve_event_credits_objective_xp_exactly_once(app):
    """The solve event must grant the daily reward only on objective completion."""
    _require_mysql(app)
    with app.app_context():
        control_user = gen_user(
            app.db,
            name="objective-control",
            email="objective-control@examplectf.com",
        )
        treatment_user = gen_user(
            app.db,
            name="objective-treatment",
            email="objective-treatment@examplectf.com",
        )

        control_challenges = [
            gen_challenge(app.db, name=f"control-{index}", value=20)
            for index in range(1, 4)
        ]
        treatment_challenges = [
            gen_challenge(app.db, name=f"treatment-{index}", value=20)
            for index in range(1, 4)
        ]

        objectives = DailyObjective.query.all()
        breach = DailyObjective.query.filter_by(
            key="daily_first_breach"
        ).one()

        def set_active_objectives(active_keys):
            for objective in objectives:
                objective.active = objective.key in active_keys
            app.db.session.commit()

        def persisted_xp(user_id):
            app.db.session.expire_all()
            user_xp = UserXP.query.filter_by(user_id=user_id).one_or_none()
            return user_xp.xp if user_xp is not None else 0

        with freeze_time(TODAY):
            set_active_objectives(set())
            gen_solve(
                app.db,
                user_id=control_user.id,
                challenge_id=control_challenges[0].id,
            )
            control_baseline_xp = persisted_xp(control_user.id)

            gen_solve(
                app.db,
                user_id=treatment_user.id,
                challenge_id=treatment_challenges[0].id,
            )
            treatment_baseline_xp = persisted_xp(treatment_user.id)

            # Only the treatment user's second solve completes the objective.
            set_active_objectives(set())
            gen_solve(
                app.db,
                user_id=control_user.id,
                challenge_id=control_challenges[1].id,
            )
            control_second_xp = persisted_xp(control_user.id)

            set_active_objectives({"daily_first_breach"})
            gen_solve(
                app.db,
                user_id=treatment_user.id,
                challenge_id=treatment_challenges[1].id,
            )
            treatment_second_xp = persisted_xp(treatment_user.id)

            second_solve_control_delta = control_second_xp - control_baseline_xp
            second_solve_treatment_delta = (
                treatment_second_xp - treatment_baseline_xp
            )
            assert (
                second_solve_treatment_delta - second_solve_control_delta
                == breach.xp_reward
            )

            breach_progress = UserDailyObjective.query.filter_by(
                user_id=treatment_user.id,
                objective_id=breach.id,
                objective_date=TODAY,
            ).one()
            assert breach_progress.progress == breach.target_value == 1
            assert breach_progress.completed is True

            set_active_objectives(set())
            gen_solve(
                app.db,
                user_id=control_user.id,
                challenge_id=control_challenges[2].id,
            )
            control_third_xp = persisted_xp(control_user.id)

            set_active_objectives({"daily_first_breach"})
            gen_solve(
                app.db,
                user_id=treatment_user.id,
                challenge_id=treatment_challenges[2].id,
            )
            treatment_third_xp = persisted_xp(treatment_user.id)

            assert treatment_third_xp - treatment_second_xp == (
                control_third_xp - control_second_xp
            )
