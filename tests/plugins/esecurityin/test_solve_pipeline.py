import threading
from datetime import date

import pytest
from flask import request
from freezegun import freeze_time
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from CTFd.exceptions.challenges import ChallengeSolveException
from CTFd.models import Notifications, Solves
from CTFd.plugins.challenges import BaseChallenge
from tests.helpers import create_ctfd, destroy_ctfd, gen_challenge, gen_user

TODAY = date(2026, 10, 21)


@pytest.fixture
def app():
    app = create_ctfd(enable_plugins=True)
    try:
        yield app
    finally:
        destroy_ctfd(app)


def _require_mysql(app):
    uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
    if not (uri.startswith("mysql") or uri.startswith("mariadb")):
        pytest.skip("Solve pipeline integration test requires MySQL/MariaDB")


def _progression_snapshot(session, user_id):
    from CTFd.plugins.esecurityin.models import (
        Achievement,
        Brooch,
        DailyObjective,
        Mission,
        UserAchievement,
        UserBrooch,
        UserDailyObjective,
        UserMission,
        UserXP,
    )

    xp = session.query(UserXP).filter_by(user_id=user_id).one_or_none()
    user_xp = (
        (
            xp.xp,
            xp.level,
            xp.streak,
            xp.longest_streak,
            xp.total_solves,
            xp.last_solve_date,
        )
        if xp
        else None
    )
    daily_objectives = {
        objective.id: objective.key
        for objective in session.query(DailyObjective).all()
    }
    missions = {mission.id: mission.key for mission in session.query(Mission).all()}

    return {
        "solves": tuple(
            sorted(
                solve.challenge_id
                for solve in session.query(Solves).filter_by(user_id=user_id).all()
            )
        ),
        "user_xp": user_xp,
        "daily_objectives": tuple(
            sorted(
                (
                    daily_objectives[row.objective_id],
                    row.objective_date,
                    row.progress,
                    row.completed,
                    row.completed_at,
                )
                for row in session.query(UserDailyObjective)
                .filter_by(user_id=user_id)
                .all()
            )
        ),
        "missions": tuple(
            sorted(
                (
                    missions[row.mission_id],
                    row.period_key,
                    row.progress,
                    row.completed,
                    row.completed_at,
                )
                for row in session.query(UserMission)
                .filter_by(user_id=user_id)
                .all()
            )
        ),
        "achievements": tuple(
            sorted(
                (
                    achievement.key,
                    earned.unlocked_at,
                )
                for earned, achievement in session.query(
                    UserAchievement, Achievement
                )
                .join(Achievement, UserAchievement.achievement_id == Achievement.id)
                .filter(UserAchievement.user_id == user_id)
                .all()
            )
        ),
        "brooches": tuple(
            sorted(
                (
                    brooch.key,
                    earned.unlocked_at,
                )
                for earned, brooch in session.query(UserBrooch, Brooch)
                .join(Brooch, UserBrooch.brooch_id == Brooch.id)
                .filter(UserBrooch.user_id == user_id)
                .all()
            )
        ),
        "notifications": tuple(
            sorted(
                (notification.title, notification.content)
                for notification in session.query(Notifications)
                .filter_by(user_id=user_id)
                .all()
            )
        ),
    }


def test_failed_duplicate_solve_does_not_leak_progression(app):
    with app.app_context():
        _require_mysql(app)

        from CTFd.plugins.esecurityin.models import (
            Achievement,
            DailyObjective,
            Mission,
            UserAchievement,
            UserBrooch,
            UserDailyObjective,
            UserMission,
            UserXP,
        )

        user = gen_user(
            app.db,
            name="duplicate_solve_regression",
            email="duplicate_solve_regression@examplectf.com",
        )
        challenge_a = gen_challenge(
            app.db,
            name="Duplicate solve regression A",
            value=20,
        )
        challenge_b = gen_challenge(
            app.db,
            name="Duplicate solve regression B",
            value=20,
        )

        assert Solves.query.filter_by(user_id=user.id).count() == 0
        assert UserXP.query.filter_by(user_id=user.id).first() is None

        with freeze_time(TODAY):
            with app.test_request_context(
                json={"submission": "flag"},
                environ_base={"REMOTE_ADDR": "127.0.0.1"},
            ):
                BaseChallenge.solve(user, None, challenge_a, request)

                with pytest.raises(ChallengeSolveException) as duplicate:
                    BaseChallenge.solve(user, None, challenge_a, request)

                assert isinstance(duplicate.value.__cause__, IntegrityError)
                assert Solves.query.filter_by(user_id=user.id).count() == 1
                app.db.session.expire_all()
                first_xp = UserXP.query.filter_by(user_id=user.id).one()
                assert first_xp.total_solves == 1

                BaseChallenge.solve(user, None, challenge_b, request)

        app.db.session.expire_all()

        solves = Solves.query.filter_by(user_id=user.id).all()
        assert len(solves) == 2
        assert {solve.challenge_id for solve in solves} == {
            challenge_a.id,
            challenge_b.id,
        }

        first_breach = DailyObjective.query.filter_by(
            key="daily_first_breach"
        ).one()
        active_operator = DailyObjective.query.filter_by(
            key="daily_operator"
        ).one()
        xp_hunter = DailyObjective.query.filter_by(
            key="daily_xp_hunter"
        ).one()
        daily_progress = {
            progress.objective_id: progress
            for progress in UserDailyObjective.query.filter_by(
                user_id=user.id,
                objective_date=TODAY,
            ).all()
        }
        assert daily_progress[first_breach.id].progress == 1
        assert daily_progress[first_breach.id].completed is True
        assert daily_progress[active_operator.id].progress == 2
        assert daily_progress[active_operator.id].completed is False
        assert daily_progress[xp_hunter.id].progress == 20
        assert daily_progress[xp_hunter.id].completed is False

        daily_runner = Mission.query.filter_by(
            key="daily_breach_runner"
        ).one()
        weekly_operator = Mission.query.filter_by(
            key="weekly_operator"
        ).one()
        special_first_strike = Mission.query.filter_by(
            key="special_first_strike"
        ).one()
        mission_progress = {
            progress.mission_id: progress
            for progress in UserMission.query.filter_by(user_id=user.id).all()
        }
        assert mission_progress[daily_runner.id].progress == 2
        assert mission_progress[daily_runner.id].completed is True
        assert mission_progress[weekly_operator.id].progress == 2
        assert mission_progress[weekly_operator.id].completed is False
        assert mission_progress[special_first_strike.id].progress == 2
        assert mission_progress[special_first_strike.id].completed is False

        first_blood = Achievement.query.filter_by(key="first_blood").one()
        assert (
            UserAchievement.query.filter_by(
                user_id=user.id,
                achievement_id=first_blood.id,
            ).count()
            == 1
        )
        assert UserBrooch.query.filter_by(user_id=user.id).count() == 2

        challenge_xp = max(10, challenge_a.value // 2)
        daily_reward = first_breach.xp_reward
        mission_reward = daily_runner.xp_reward
        achievement_reward = first_blood.xp_reward
        xp = UserXP.query.filter_by(user_id=user.id).one()
        assert xp.total_solves == 2
        assert xp.xp == (
            challenge_xp * 2
            + daily_reward
            + mission_reward
            + achievement_reward
        )
        assert (
            Notifications.query.filter_by(
                user_id=user.id,
                title="⚡ XP Gained",
            ).count()
            == 2
        )


def test_successful_solves_update_complete_progression_pipeline(app):
    with app.app_context():
        _require_mysql(app)

        from CTFd.plugins.esecurityin.models import (
            Achievement,
            Brooch,
            DailyObjective,
            Mission,
            UserAchievement,
            UserBrooch,
            UserDailyObjective,
            UserMission,
            UserXP,
        )

        user = gen_user(
            app.db,
            name="solve_pipeline_golden_path",
            email="solve_pipeline_golden_path@examplectf.com",
        )
        challenges = [
            gen_challenge(
                app.db,
                name=f"Golden path challenge {index}",
                value=20,
            )
            for index in range(1, 4)
        ]

        assert Solves.query.filter_by(user_id=user.id).count() == 0
        assert UserXP.query.filter_by(user_id=user.id).first() is None

        with freeze_time(TODAY):
            with app.test_request_context(
                json={"submission": "flag"},
                environ_base={"REMOTE_ADDR": "127.0.0.1"},
            ):
                for challenge in challenges:
                    BaseChallenge.solve(user, None, challenge, request)

        app.db.session.expire_all()

        solves = Solves.query.filter_by(user_id=user.id).all()
        assert len(solves) == 3
        assert {solve.challenge_id for solve in solves} == {
            challenge.id for challenge in challenges
        }

        daily_objectives = {
            objective.key: objective
            for objective in DailyObjective.query.all()
        }
        daily_objectives_by_id = {
            objective.id: objective for objective in daily_objectives.values()
        }
        daily_progress = {
            daily_objectives_by_id[progress.objective_id].key: progress
            for progress in UserDailyObjective.query.filter_by(
                user_id=user.id,
                objective_date=TODAY,
            ).all()
        }
        assert daily_progress["daily_first_breach"].progress == 1
        assert daily_progress["daily_first_breach"].completed is True
        assert daily_progress["daily_operator"].progress == 3
        assert daily_progress["daily_operator"].completed is True
        assert daily_progress["daily_xp_hunter"].progress == 30
        assert daily_progress["daily_xp_hunter"].completed is False

        missions = {mission.key: mission for mission in Mission.query.all()}
        missions_by_id = {mission.id: mission for mission in missions.values()}
        mission_progress = {
            missions_by_id[progress.mission_id].key: progress
            for progress in UserMission.query.filter_by(user_id=user.id).all()
        }
        assert mission_progress["daily_breach_runner"].progress == 2
        assert mission_progress["daily_breach_runner"].completed is True
        assert mission_progress["daily_xp_hunter"].progress == 30
        assert mission_progress["daily_xp_hunter"].completed is False
        assert mission_progress["weekly_operator"].progress == 3
        assert mission_progress["weekly_operator"].completed is False
        assert mission_progress["weekly_xp_hunter"].progress == 30
        assert mission_progress["weekly_xp_hunter"].completed is False
        assert mission_progress["special_first_strike"].progress == 3
        assert mission_progress["special_first_strike"].completed is False

        achievements = {
            achievement.key: achievement
            for achievement in Achievement.query.all()
        }
        achievements_by_id = {
            achievement.id: achievement for achievement in achievements.values()
        }
        earned_achievement_keys = {
            achievements_by_id[earned.achievement_id].key
            for earned in UserAchievement.query.filter_by(
                user_id=user.id
            ).all()
        }
        assert earned_achievement_keys == {"first_blood", "getting_started"}

        brooches = {brooch.id: brooch for brooch in Brooch.query.all()}
        earned_brooch_keys = {
            brooches[earned.brooch_id].key
            for earned in UserBrooch.query.filter_by(user_id=user.id).all()
        }
        assert earned_brooch_keys == {"first_breach", "breach_runner"}

        challenge_xp = sum(max(10, challenge.value // 2) for challenge in challenges)
        objective_reward = sum(
            daily_objectives[key].xp_reward
            for key in ("daily_first_breach", "daily_operator")
        )
        mission_reward = missions["daily_breach_runner"].xp_reward
        achievement_reward = sum(
            achievements[key].xp_reward
            for key in ("first_blood", "getting_started")
        )
        xp = UserXP.query.filter_by(user_id=user.id).one()
        assert xp.xp == (
            challenge_xp
            + objective_reward
            + mission_reward
            + achievement_reward
        )
        assert xp.total_solves == 3
        assert xp.level == 1
        assert xp.streak == 1
        assert xp.longest_streak == 1
        assert xp.last_solve_date == TODAY

        notifications = Notifications.query.filter_by(user_id=user.id).all()
        notification_counts = {}
        for notification in notifications:
            notification_counts[notification.title] = (
                notification_counts.get(notification.title, 0) + 1
            )
        assert notification_counts == {
            "⚡ XP Gained": 3,
            "🎯 Objective Complete": 2,
            "🚀 Mission Complete": 1,
            "🏆 Achievement Unlocked": 2,
            "📌 Brooch Unlocked": 2,
        }


def test_solve_event_failure_rolls_back_progression(app, monkeypatch):
    with app.app_context():
        _require_mysql(app)

        from CTFd.plugins.esecurityin.services.notification_service import (
            NotificationService,
        )

        user = gen_user(
            app.db,
            name="solve_pipeline_rollback",
            email="solve_pipeline_rollback@examplectf.com",
        )
        first_challenge = gen_challenge(
            app.db,
            name="Rollback baseline challenge",
            value=20,
        )
        failing_challenge = gen_challenge(
            app.db,
            name="Rollback failure challenge",
            value=900,
        )

        with freeze_time(TODAY):
            with app.test_request_context(
                json={"submission": "flag"},
                environ_base={"REMOTE_ADDR": "127.0.0.1"},
            ):
                BaseChallenge.solve(user, None, first_challenge, request)

        session_factory = sessionmaker(bind=app.db.engine)
        with session_factory() as verification_session:
            baseline = _progression_snapshot(verification_session, user.id)

        original_create_notification = NotificationService._create
        scheduled_notifications = []

        def record_notification(user_id, title, content):
            scheduled_notifications.append(title)
            return original_create_notification(user_id, title, content)

        monkeypatch.setattr(
            NotificationService,
            "_create",
            staticmethod(record_notification),
        )
        original_brooch_notification = NotificationService.brooch_unlocked
        brooch_notifications = []
        failure_message = "injected failure after brooch notifications"

        def fail_after_brooch_notification(user_id, brooch):
            original_brooch_notification(user_id=user_id, brooch=brooch)
            brooch_notifications.append(brooch["key"])
            if len(brooch_notifications) == 2:
                raise RuntimeError(failure_message)

        monkeypatch.setattr(
            NotificationService,
            "brooch_unlocked",
            fail_after_brooch_notification,
        )

        with freeze_time(TODAY):
            with app.test_request_context(
                json={"submission": "flag"},
                environ_base={"REMOTE_ADDR": "127.0.0.1"},
            ):
                with pytest.raises(RuntimeError, match=failure_message):
                    BaseChallenge.solve(user, None, failing_challenge, request)

        app.db.session.rollback()

        assert brooch_notifications == ["breach_runner", "xp_hunter"]
        assert scheduled_notifications == [
            "⚡ XP Gained",
            "🎯 Objective Complete",
            "🚀 Mission Complete",
            "🚀 Mission Complete",
            "🏆 Achievement Unlocked",
            "📌 Brooch Unlocked",
            "📌 Brooch Unlocked",
        ]

        with session_factory() as verification_session:
            after_rollback = _progression_snapshot(
                verification_session,
                user.id,
            )

        assert after_rollback == baseline


def test_concurrent_first_solves_award_progression_once(app, monkeypatch):
    _require_mysql(app)

    from CTFd.plugins.esecurityin.models import (
        Achievement,
        DailyObjective,
        Mission,
        UserAchievement,
        UserBrooch,
        UserDailyObjective,
        UserMission,
        UserXP,
    )
    from CTFd.plugins.esecurityin.services.notification_service import (
        NotificationService,
    )

    with app.app_context():
        user = gen_user(
            app.db,
            name="concurrent_first_solve",
            email="concurrent_first_solve@examplectf.com",
        )
        challenges = [
            gen_challenge(
                app.db,
                name=f"Concurrent first solve {index}",
                value=20,
            )
            for index in range(2)
        ]
        user_id = user.id
        challenge_ids = [challenge.id for challenge in challenges]

        assert UserXP.query.filter_by(user_id=user_id).one_or_none() is None
        app.db.session.remove()

    first_solve_lock_barrier = threading.Barrier(2)
    errors = []
    worker_session_ids = []
    first_solve_lock_user_ids = []
    notification_session_ids = []
    notification_calls = []
    results_lock = threading.Lock()
    original_create_notification = NotificationService._create
    original_execute = Session.execute

    def synchronize_first_solve_user_lock(
        session,
        statement,
        params=None,
        *args,
        **kwargs,
    ):
        sql = str(statement)
        if (
            "FROM users" in sql
            and "FOR UPDATE" in sql
            and params
            and params.get("user_id") == user_id
        ):
            with results_lock:
                first_solve_lock_user_ids.append(params["user_id"])
            first_solve_lock_barrier.wait(timeout=15)
        return original_execute(
            session,
            statement,
            params,
            *args,
            **kwargs,
        )

    def track_notification_session(user_id, title, content):
        with results_lock:
            notification_session_ids.append(id(app.db.session()))
            notification_calls.append(title)
        return original_create_notification(user_id, title, content)

    monkeypatch.setattr(
        NotificationService,
        "_create",
        staticmethod(track_notification_session),
    )
    monkeypatch.setattr(Session, "execute", synchronize_first_solve_user_lock)

    def worker(challenge_id):
        with app.test_request_context(
            json={"submission": "flag"},
            environ_base={"REMOTE_ADDR": "127.0.0.1"},
        ):
            session = app.db.session()
            try:
                with results_lock:
                    worker_session_ids.append(id(session))
                session.add(
                    Solves(
                        user_id=user_id,
                        challenge_id=challenge_id,
                        ip="127.0.0.1",
                        provided="rightkey",
                    )
                )
                session.commit()
            except Exception as exc:  # pragma: no cover - surfaced by assertion
                with results_lock:
                    errors.append(exc)
                session.rollback()
            finally:
                app.db.session.remove()

    with freeze_time(TODAY):
        threads = [
            threading.Thread(target=worker, args=(challenge_id,))
            for challenge_id in challenge_ids
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=45)

    assert not any(thread.is_alive() for thread in threads)
    assert len(set(worker_session_ids)) == 2
    assert first_solve_lock_user_ids == [user_id, user_id]
    assert errors == []
    assert set(notification_session_ids).issubset(set(worker_session_ids))

    with app.app_context():
        solves = Solves.query.filter_by(user_id=user_id).all()
        assert len(solves) == 2
        assert {solve.challenge_id for solve in solves} == set(challenge_ids)

        daily_first_breach = DailyObjective.query.filter_by(
            key="daily_first_breach"
        ).one()
        daily_breach_runner = Mission.query.filter_by(
            key="daily_breach_runner"
        ).one()
        first_blood = Achievement.query.filter_by(key="first_blood").one()

        daily_progress = UserDailyObjective.query.filter_by(
            user_id=user_id,
            objective_id=daily_first_breach.id,
            objective_date=TODAY,
        ).one()
        assert daily_progress.progress == daily_first_breach.target_value == 1
        assert daily_progress.completed is True

        mission_progress = UserMission.query.filter_by(
            user_id=user_id,
            mission_id=daily_breach_runner.id,
            period_key=TODAY.isoformat(),
        ).one()
        assert mission_progress.progress == 2
        assert mission_progress.completed is True
        assert UserMission.query.filter_by(user_id=user_id).count() == len(
            Mission.query.filter_by(active=True).all()
        )

        assert (
            UserAchievement.query.filter_by(
                user_id=user_id,
                achievement_id=first_blood.id,
            ).count()
            == 1
        )
        assert UserAchievement.query.filter_by(user_id=user_id).count() == 1
        assert UserBrooch.query.filter_by(user_id=user_id).count() == 2

        expected_xp = (
            2 * 10
            + daily_first_breach.xp_reward
            + daily_breach_runner.xp_reward
            + first_blood.xp_reward
        )
        user_xp = UserXP.query.filter_by(user_id=user_id).one()
        assert user_xp.xp == expected_xp
        assert user_xp.total_solves == 2

        notification_counts = {}
        for notification in Notifications.query.filter_by(user_id=user_id).all():
            notification_counts[notification.title] = (
                notification_counts.get(notification.title, 0) + 1
            )
        assert notification_counts == {
            "⚡ XP Gained": 2,
            "🎯 Objective Complete": 1,
            "🚀 Mission Complete": 1,
            "🏆 Achievement Unlocked": 1,
            "📌 Brooch Unlocked": 2,
        }, {"persisted": notification_counts, "created": notification_calls}


def test_solve_listener_does_not_run_for_apps_without_plugin(app):
    plain_app = create_ctfd(enable_plugins=False)
    try:
        with plain_app.app_context():
            user = gen_user(
                plain_app.db,
                name="non_plugin_solve",
                email="non_plugin_solve@examplectf.com",
            )
            challenge = gen_challenge(
                plain_app.db,
                name="Non-plugin challenge",
                value=20,
            )
            solve = Solves(
                user_id=user.id,
                challenge_id=challenge.id,
                ip="127.0.0.1",
                provided="rightkey",
            )
            plain_app.db.session.add(solve)
            plain_app.db.session.commit()
            assert Solves.query.filter_by(
                user_id=user.id,
                challenge_id=challenge.id,
            ).count() == 1
    finally:
        destroy_ctfd(plain_app)


def test_concurrent_solves_complete_mission_and_reward_once(app):
    _require_mysql(app)

    from CTFd.plugins.esecurityin.models import (
        Achievement,
        Brooch,
        DailyObjective,
        Mission,
        UserAchievement,
        UserBrooch,
        UserDailyObjective,
        UserMission,
        UserXP,
    )

    with app.app_context():
        user = gen_user(
            app.db,
            name="concurrent_mission_completion",
            email="concurrent_mission_completion@examplectf.com",
        )
        challenges = [
            gen_challenge(
                app.db,
                name=f"Mission completion race {index}",
                value=20,
            )
            for index in range(2)
        ]
        user_id = user.id
        challenge_ids = [challenge.id for challenge in challenges]
        mission = Mission.query.filter_by(key="daily_breach_runner").one()
        for item in Mission.query.all():
            item.active = item.id == mission.id
        for objective in DailyObjective.query.all():
            objective.active = False
        for achievement in Achievement.query.all():
            achievement.active = False
        for brooch in Brooch.query.all():
            brooch.active = False
        app.db.session.add(
            UserXP(
                user_id=user_id,
                xp=100,
                level=1,
                streak=1,
                longest_streak=1,
                total_solves=0,
                last_solve_date=TODAY,
            )
        )
        app.db.session.add(
            UserMission(
                user_id=user_id,
                mission_id=mission.id,
                period_key=TODAY.isoformat(),
                progress=mission.target_value - 1,
                completed=False,
            )
        )
        app.db.session.commit()
        mission_id = mission.id
        mission_reward = mission.xp_reward

    barrier = threading.Barrier(2)
    errors = []
    sessions = []
    result_lock = threading.Lock()

    def worker(challenge_id):
        with app.test_request_context(
            json={"submission": "flag"},
            environ_base={"REMOTE_ADDR": "127.0.0.1"},
        ):
            session = app.db.session()
            try:
                with result_lock:
                    sessions.append(session)
                barrier.wait(timeout=15)
                session.add(
                    Solves(
                        user_id=user_id,
                        challenge_id=challenge_id,
                        ip="127.0.0.1",
                        provided="rightkey",
                    )
                )
                session.commit()
            except Exception as exc:  # pragma: no cover - surfaced by assertion
                with result_lock:
                    errors.append(exc)
                session.rollback()
            finally:
                app.db.session.remove()

    with freeze_time(TODAY):
        threads = [
            threading.Thread(target=worker, args=(challenge_id,))
            for challenge_id in challenge_ids
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=45)

    assert not any(thread.is_alive() for thread in threads)
    assert len(sessions) == 2
    assert sessions[0] is not sessions[1]
    assert errors == []

    with app.app_context():
        assert Solves.query.filter_by(user_id=user_id).count() == 2
        mission_progress = UserMission.query.filter_by(
            user_id=user_id,
            mission_id=mission_id,
            period_key=TODAY.isoformat(),
        ).one()
        assert mission_progress.progress == 2
        assert mission_progress.completed is True
        assert mission_progress.completed_at is not None
        assert (
            Notifications.query.filter_by(
                user_id=user_id,
                title="🚀 Mission Complete",
            ).count()
            == 1
        )
        assert (
            Notifications.query.filter_by(
                user_id=user_id,
                title="⚡ XP Gained",
            ).count()
            == 2
        )
        persisted_xp = UserXP.query.filter_by(user_id=user_id).one()
        assert persisted_xp.xp == 100 + (2 * 10) + mission_reward
        assert persisted_xp.total_solves == 2
        assert UserDailyObjective.query.filter_by(user_id=user_id).count() == 0
        assert UserAchievement.query.filter_by(user_id=user_id).count() == 0
        assert UserBrooch.query.filter_by(user_id=user_id).count() == 0


def test_concurrent_brooch_unlock_creates_one_record_and_notification(app):
    _require_mysql(app)

    from CTFd.plugins.esecurityin.models import (
        Achievement,
        Brooch,
        UserAchievement,
        UserBrooch,
        UserXP,
    )
    from CTFd.plugins.esecurityin.services.brooch_service import BroochService
    from CTFd.plugins.esecurityin.services.notification_service import (
        NotificationService,
    )

    with app.app_context():
        user = gen_user(
            app.db,
            name="concurrent_brooch_unlock",
            email="concurrent_brooch_unlock@examplectf.com",
        )
        user_id = user.id
        brooch = Brooch.query.filter_by(key="first_breach").one()
        for item in Brooch.query.all():
            item.active = item.id == brooch.id
        first_blood = Achievement.query.filter_by(key="first_blood").one()
        app.db.session.add(
            UserAchievement(
                user_id=user_id,
                achievement_id=first_blood.id,
            )
        )
        app.db.session.add(
            UserXP(
                user_id=user_id,
                xp=73,
                level=1,
                streak=0,
                longest_streak=0,
                total_solves=0,
            )
        )
        app.db.session.commit()
        brooch_id = brooch.id
        engine = app.db.engine

    barrier = threading.Barrier(2)
    errors = []
    results = []
    sessions = []
    result_lock = threading.Lock()

    def synchronize_absent_brooch_reads(
        connection,
        cursor,
        statement,
        parameters,
        context,
        executemany,
    ):
        normalized_statement = " ".join(statement.lower().split())
        if (
            normalized_statement.startswith("select id from esecurityin_user_brooches")
            and "where user_id =" in normalized_statement
            and "and brooch_id =" in normalized_statement
        ):
            barrier.wait(timeout=15)

    def worker():
        with app.app_context():
            session = app.db.session()
            try:
                with result_lock:
                    sessions.append(session)
                unlocked = BroochService.process_unlocks(session, user_id)
                for item in unlocked:
                    NotificationService.brooch_unlocked(
                        user_id=user_id,
                        brooch=item,
                    )
                session.commit()
                with result_lock:
                    results.append(unlocked)
            except Exception as exc:  # pragma: no cover - surfaced by assertion
                with result_lock:
                    errors.append(exc)
                session.rollback()
            finally:
                app.db.session.remove()

    event.listen(engine, "after_cursor_execute", synchronize_absent_brooch_reads)
    try:
        threads = [threading.Thread(target=worker) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=45)
    finally:
        event.remove(engine, "after_cursor_execute", synchronize_absent_brooch_reads)

    assert not any(thread.is_alive() for thread in threads)
    assert len(sessions) == 2
    assert sessions[0] is not sessions[1]
    assert errors == []
    assert sorted(len(unlocked) for unlocked in results) == [0, 1]
    assert [unlocked[0]["id"] for unlocked in results if unlocked] == [brooch_id]

    with app.app_context():
        assert (
            UserBrooch.query.filter_by(
                user_id=user_id,
                brooch_id=brooch_id,
            ).count()
            == 1
        )
        assert (
            Notifications.query.filter_by(
                user_id=user_id,
                title="📌 Brooch Unlocked",
            ).count()
            == 1
        )
        assert UserXP.query.filter_by(user_id=user_id).one().xp == 73
