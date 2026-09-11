from datetime import date, datetime, timezone

from sqlalchemy import text

from CTFd.models import db

from ..models import Mission, UserMission


class MissionService:
    MISSIONS = [
        {
            "key": "daily_breach_runner",
            "name": "Breach Runner",
            "description": "Solve 2 challenges today.",
            "icon": "⚡",
            "mission_type": "daily",
            "objective_type": "solves",
            "target_value": 2,
            "xp_reward": 40,
            "active": True,
        },
        {
            "key": "daily_xp_hunter",
            "name": "XP Hunter",
            "description": "Earn 100 challenge XP today.",
            "icon": "🎯",
            "mission_type": "daily",
            "objective_type": "xp",
            "target_value": 100,
            "xp_reward": 50,
            "active": True,
        },
        {
            "key": "weekly_operator",
            "name": "Weekly Operator",
            "description": "Solve 10 challenges this week.",
            "icon": "🔥",
            "mission_type": "weekly",
            "objective_type": "solves",
            "target_value": 10,
            "xp_reward": 150,
            "active": True,
        },
        {
            "key": "weekly_xp_hunter",
            "name": "Weekly XP Hunter",
            "description": "Earn 500 challenge XP this week.",
            "icon": "💎",
            "mission_type": "weekly",
            "objective_type": "xp",
            "target_value": 500,
            "xp_reward": 200,
            "active": True,
        },
        {
            "key": "special_first_strike",
            "name": "First Strike",
            "description": "Solve 5 challenges to complete this special mission.",
            "icon": "☠️",
            "mission_type": "special",
            "objective_type": "solves",
            "target_value": 5,
            "xp_reward": 100,
            "active": True,
        },
    ]

    @classmethod
    def seed_missions(cls):
        for definition in cls.MISSIONS:
            existing = Mission.query.filter_by(
                key=definition["key"]
            ).first()

            if existing:
                continue

            mission = Mission(**definition)
            db.session.add(mission)

        db.session.commit()

    @classmethod
    def get_active_missions(cls, mission_type=None):
        query = Mission.query.filter_by(
            active=True
        )

        if mission_type:
            query = query.filter_by(
                mission_type=mission_type
            )

        return query.order_by(
            Mission.id.asc()
        ).all()

    @classmethod
    def get_period_key(cls, mission_type, current_date=None):
        if current_date is None:
            current_date = date.today()

        if mission_type == "daily":
            return current_date.isoformat()

        if mission_type == "weekly":
            year, week, _ = current_date.isocalendar()
            return f"{year}-W{week:02d}"

        return "special"

    @classmethod
    def get_or_create_progress(
        cls,
        user_id,
        mission,
        current_date=None,
        session=None,
    ):
        if current_date is None:
            current_date = date.today()

        period_key = cls.get_period_key(
            mission.mission_type,
            current_date,
        )

        query = (
            UserMission.query
            .filter_by(
                user_id=user_id,
                mission_id=mission.id,
                period_key=period_key,
            )
            .first()
        )

        if query:
            return query

        progress = UserMission(
            user_id=user_id,
            mission_id=mission.id,
            period_key=period_key,
            progress=0,
            completed=False,
            completed_at=None,
        )

        if session is not None:
            session.add(progress)
            session.flush()
        else:
            db.session.add(progress)
            db.session.flush()

        return progress

    @classmethod
    def get_player_missions(cls, user_id, mission_type=None):
        missions = cls.get_active_missions(
            mission_type=mission_type
        )

        result = []

        for mission in missions:
            progress = cls.get_or_create_progress(
                user_id=user_id,
                mission=mission,
            )

            result.append(
                {
                    "id": mission.id,
                    "key": mission.key,
                    "name": mission.name,
                    "description": mission.description,
                    "icon": mission.icon,
                    "mission_type": mission.mission_type,
                    "objective_type": mission.objective_type,
                    "target_value": mission.target_value,
                    "xp_reward": mission.xp_reward,
                    "period_key": progress.period_key,
                    "progress": progress.progress,
                    "completed": progress.completed,
                    "remaining": max(
                        0,
                        mission.target_value - progress.progress,
                    ),
                    "completed_at": (
                        progress.completed_at.isoformat()
                        if progress.completed_at
                        else None
                    ),
                }
            )

        return result

    @classmethod
    def process_solve(
        cls,
        session,
        user_id,
        challenge_xp,
    ):
        current_date = datetime.now(
            timezone.utc
        ).date()

        missions = (
            session.execute(
                text(
                    """
                    SELECT
                        id,
                        `key`,
                        name,
                        description,
                        icon,
                        mission_type,
                        objective_type,
                        target_value,
                        xp_reward
                    FROM esecurityin_missions
                    WHERE active = 1
                    ORDER BY id ASC
                    """
                )
            )
            .fetchall()
        )

        newly_completed = []

        for mission in missions:
            (
                mission_id,
                key,
                name,
                description,
                icon,
                mission_type,
                objective_type,
                target_value,
                xp_reward,
            ) = mission

            period_key = cls.get_period_key(
                mission_type,
                current_date,
            )

            result = session.execute(
                text(
                    """
                    SELECT
                        id,
                        progress,
                        completed
                    FROM esecurityin_user_missions
                    WHERE user_id = :user_id
                      AND mission_id = :mission_id
                      AND period_key = :period_key
                    """
                ),
                {
                    "user_id": user_id,
                    "mission_id": mission_id,
                    "period_key": period_key,
                },
            )

            user_mission = result.fetchone()

            if user_mission:
                user_mission_id = user_mission[0]
                current_progress = user_mission[1] or 0
                already_completed = bool(
                    user_mission[2]
                )
            else:
                session.execute(
                    text(
                        """
                        INSERT INTO esecurityin_user_missions
                        (
                            user_id,
                            mission_id,
                            period_key,
                            progress,
                            completed,
                            completed_at
                        )
                        VALUES
                        (
                            :user_id,
                            :mission_id,
                            :period_key,
                            0,
                            0,
                            NULL
                        )
                        """
                    ),
                    {
                        "user_id": user_id,
                        "mission_id": mission_id,
                        "period_key": period_key,
                    },
                )

                result = session.execute(
                    text(
                        """
                        SELECT
                            id,
                            progress,
                            completed
                        FROM esecurityin_user_missions
                        WHERE user_id = :user_id
                          AND mission_id = :mission_id
                          AND period_key = :period_key
                        """
                    ),
                    {
                        "user_id": user_id,
                        "mission_id": mission_id,
                        "period_key": period_key,
                    },
                )

                user_mission = result.fetchone()

                user_mission_id = user_mission[0]
                current_progress = 0
                already_completed = False

            if already_completed:
                continue

            if objective_type == "solves":
                new_progress = (
                    current_progress + 1
                )

            elif objective_type == "xp":
                new_progress = (
                    current_progress + challenge_xp
                )

            else:
                new_progress = current_progress

            new_progress = min(
                new_progress,
                target_value,
            )

            is_completed = (
                new_progress >= target_value
            )

            session.execute(
                text(
                    """
                    UPDATE esecurityin_user_missions
                    SET
                        progress = :progress,
                        completed = :completed,
                        completed_at =
                            CASE
                                WHEN :completed = 1
                                THEN CURRENT_TIMESTAMP(6)
                                ELSE completed_at
                            END
                    WHERE id = :id
                    """
                ),
                {
                    "progress": new_progress,
                    "completed": int(
                        is_completed
                    ),
                    "id": user_mission_id,
                },
            )

            if is_completed:
                newly_completed.append(
                    {
                        "id": mission_id,
                        "key": key,
                        "name": name,
                        "description": description,
                        "icon": icon,
                        "mission_type": mission_type,
                        "xp_reward": xp_reward,
                        "progress": new_progress,
                        "target_value": target_value,
                        "period_key": period_key,
                    }
                )

        return newly_completed