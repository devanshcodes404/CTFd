from datetime import date, datetime

import pytest

from CTFd.models import Users, db
from tests.helpers import (
    create_ctfd,
    destroy_ctfd,
    login_as_user,
    register_user,
)


@pytest.fixture
def app():
    app = create_ctfd(enable_plugins=True)
    try:
        yield app
    finally:
        destroy_ctfd(app)


def _progression_state(user_id):
    from CTFd.plugins.esecurityin.models import (
        UserAchievement,
        UserBrooch,
        UserDailyObjective,
        UserMission,
        UserXP,
    )

    xp = UserXP.query.filter_by(user_id=user_id).one_or_none()
    return {
        "xp": (
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
        ),
        "daily_objectives": tuple(
            sorted(
                (
                    progress.objective_id,
                    progress.objective_date,
                    progress.progress,
                    progress.completed,
                )
                for progress in UserDailyObjective.query.filter_by(
                    user_id=user_id
                ).all()
            )
        ),
        "missions": tuple(
            sorted(
                (
                    progress.mission_id,
                    progress.period_key,
                    progress.progress,
                    progress.completed,
                )
                for progress in UserMission.query.filter_by(user_id=user_id).all()
            )
        ),
        "achievements": tuple(
            sorted(
                UserAchievement.query.filter_by(user_id=user_id)
                .with_entities(UserAchievement.achievement_id)
                .all()
            )
        ),
        "brooches": tuple(
            sorted(
                UserBrooch.query.filter_by(user_id=user_id)
                .with_entities(UserBrooch.brooch_id)
                .all()
            )
        ),
    }


def test_user_progression_routes_reject_forged_user_ids(app):
    with app.app_context():
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
        from CTFd.plugins.esecurityin.services.mission_service import MissionService

        register_user(
            app, name="progression-owner-a", email="owner-a@examplectf.com"
        )
        register_user(
            app, name="progression-owner-b", email="owner-b@examplectf.com"
        )
        user_a = Users.query.filter_by(name="progression-owner-a").one()
        user_b = Users.query.filter_by(name="progression-owner-b").one()

        objective = DailyObjective.query.filter_by(key="daily_first_breach").one()
        mission = Mission.query.filter_by(key="daily_breach_runner").one()
        achievement = Achievement.query.filter_by(key="first_blood").one()
        brooch = Brooch.query.filter_by(key="first_breach").one()
        db.session.add_all(
            [
                UserXP(
                    user_id=user_b.id,
                    xp=99173,
                    level=199,
                    streak=17,
                    longest_streak=21,
                    total_solves=37,
                ),
                UserDailyObjective(
                    user_id=user_b.id,
                    objective_id=objective.id,
                    objective_date=date.today(),
                    progress=1,
                    completed=True,
                    completed_at=datetime.utcnow(),
                ),
                UserMission(
                    user_id=user_b.id,
                    mission_id=mission.id,
                    period_key=MissionService.get_period_key(mission.mission_type),
                    progress=2,
                    completed=True,
                    completed_at=datetime.utcnow(),
                ),
                UserAchievement(
                    user_id=user_b.id,
                    achievement_id=achievement.id,
                ),
                UserBrooch(
                    user_id=user_b.id,
                    brooch_id=brooch.id,
                    unlocked_at=datetime.utcnow(),
                ),
            ]
        )
        db.session.commit()
        user_a_id = user_a.id
        user_b_id = user_b.id
        b_state_before = _progression_state(user_b_id)

        with login_as_user(app, name="progression-owner-a") as client:
            for path in (
                f"/api/v1/esecurityin/user/{user_b_id}",
                f"/api/v1/esecurityin/user/{user_b_id}/achievements",
                f"/api/v1/esecurityin/user/{user_b_id}/achievements/all",
                f"/api/v1/esecurityin/profile/{user_b_id}",
                f"/api/v1/esecurityin/user/{user_b_id}/daily-objectives",
            ):
                response = client.get(path, json={})
                assert response.status_code == 403, path
                assert response.get_json() == {"error": "forbidden"}
                assert "99173" not in response.get_data(as_text=True)

            forged_missions = client.get(
                f"/api/v1/esecurityin/missions?user_id={user_b_id}", json={}
            )
            assert forged_missions.status_code == 200
            mission_data = forged_missions.get_json()
            assert mission_data["user_id"] == user_a_id
            owner_mission = next(
                item
                for item in mission_data["missions"]
                if item["key"] == "daily_breach_runner"
            )
            assert owner_mission["progress"] == 0
            assert owner_mission["completed"] is False

        db.session.expire_all()
        assert _progression_state(user_b_id) == b_state_before
        assert UserXP.query.filter_by(user_id=user_a_id).one_or_none() is None
        assert UserDailyObjective.query.filter_by(user_id=user_a_id).count() == 0
        assert UserMission.query.filter_by(user_id=user_a_id).count() == 0
        assert UserAchievement.query.filter_by(user_id=user_a_id).count() == 0
        assert UserBrooch.query.filter_by(user_id=user_a_id).count() == 0


def test_user_progression_routes_require_authentication_but_leaderboard_is_public(
    app,
):
    with app.app_context():
        register_user(
            app,
            name="progression-anon-target",
            email="anon-target@examplectf.com",
        )
        target = Users.query.filter_by(name="progression-anon-target").one()
        target_id = target.id

        with app.test_client() as client:
            for path in (
                f"/api/v1/esecurityin/user/{target_id}",
                f"/api/v1/esecurityin/user/{target_id}/achievements",
                f"/api/v1/esecurityin/user/{target_id}/achievements/all",
                f"/api/v1/esecurityin/profile/{target_id}",
                f"/api/v1/esecurityin/user/{target_id}/daily-objectives",
                "/api/v1/esecurityin/missions",
            ):
                response = client.get(path, json={})
                assert response.status_code == 403, path

            leaderboard = client.get("/api/v1/esecurityin/leaderboard")
            assert leaderboard.status_code == 200
