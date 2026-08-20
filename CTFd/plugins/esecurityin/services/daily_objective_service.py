from datetime import date, datetime, timezone

from sqlalchemy import text

from CTFd.models import db

from ..models import DailyObjective, UserDailyObjective


class DailyObjectiveService:

    OBJECTIVES = [
        {
            "key": "daily_first_breach",
            "name": "First Breach",
            "description": "Solve 1 challenge today.",
            "icon": "🎯",
            "objective_type": "daily_solves",
            "target_value": 1,
            "xp_reward": 25,
        },
        {
            "key": "daily_operator",
            "name": "Active Operator",
            "description": "Solve 3 challenges today.",
            "icon": "⚔️",
            "objective_type": "daily_solves",
            "target_value": 3,
            "xp_reward": 50,
        },
        {
            "key": "daily_xp_hunter",
            "name": "XP Hunter",
            "description": "Earn 100 XP from challenges today.",
            "icon": "⚡",
            "objective_type": "daily_xp",
            "target_value": 100,
            "xp_reward": 50,
        },
    ]

    @classmethod
    def seed_objectives(cls):
        """
        Create the default daily-objective definitions
        if they do not already exist.
        """

        for definition in cls.OBJECTIVES:

            existing = (
                DailyObjective.query
                .filter_by(
                    key=definition["key"]
                )
                .first()
            )

            if existing:
                continue

            objective = DailyObjective(
                **definition
            )

            db.session.add(
                objective
            )

        db.session.commit()

    @classmethod
    def get_active_objectives(cls):
        """
        Return all currently active objective definitions.
        """

        return (
            DailyObjective.query
            .filter_by(active=True)
            .order_by(
                DailyObjective.id.asc()
            )
            .all()
        )

    @classmethod
    def get_or_create_daily_progress(
        cls,
        user_id,
        objective,
        objective_date=None,
        session=None,
    ):
        """
        Return today's UserDailyObjective row.

        Creates the row if it does not exist yet.
        """

        if objective_date is None:
            objective_date = date.today()

        query = (
            UserDailyObjective.query
            .filter_by(
                user_id=user_id,
                objective_id=objective.id,
                objective_date=objective_date,
            )
            .first()
        )

        if query:
            return query

        progress = UserDailyObjective(
            user_id=user_id,
            objective_id=objective.id,
            objective_date=objective_date,
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
    def get_today(cls, user_id):
        """
        Return today's objectives and player progress.
        """

        today = date.today()

        objectives = cls.get_active_objectives()

        result = []

        for objective in objectives:

            progress = (
                UserDailyObjective.query
                .filter_by(
                    user_id=user_id,
                    objective_id=objective.id,
                    objective_date=today,
                )
                .first()
            )

            current_progress = (
                progress.progress
                if progress
                else 0
            )

            completed = (
                progress.completed
                if progress
                else False
            )

            result.append(
                {
                    "id": objective.id,
                    "key": objective.key,
                    "name": objective.name,
                    "description": objective.description,
                    "icon": objective.icon,
                    "objective_type": objective.objective_type,
                    "target_value": objective.target_value,
                    "xp_reward": objective.xp_reward,
                    "progress": current_progress,
                    "completed": completed,
                    "remaining": max(
                        0,
                        objective.target_value
                        - current_progress,
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
        """
        Update daily objectives after a successful challenge solve.

        Uses the existing SQLAlchemy transaction so objective
        progress and rewards remain part of the same solve transaction.

        Returns newly completed objectives.
        """

        today = date.today()

        objectives = (
            session.execute(
                text(
                    """
                    SELECT
                        id,
                        `key`,
                        name,
                        description,
                        icon,
                        objective_type,
                        target_value,
                        xp_reward
                    FROM esecurityin_daily_objectives
                    WHERE active = 1
                    ORDER BY id ASC
                    """
                )
            )
            .fetchall()
        )

        newly_completed = []

        for objective in objectives:

            (
                objective_id,
                key,
                name,
                description,
                icon,
                objective_type,
                target_value,
                xp_reward,
            ) = objective

            result = session.execute(
                text(
                    """
                    SELECT
                        id,
                        progress,
                        completed
                    FROM esecurityin_user_daily_objectives
                    WHERE user_id = :user_id
                      AND objective_id = :objective_id
                      AND objective_date = :objective_date
                    FOR UPDATE
                    """
                ),
                {
                    "user_id": user_id,
                    "objective_id": objective_id,
                    "objective_date": today,
                },
            )

            user_objective = result.fetchone()

            if user_objective:

                user_objective_id = (
                    user_objective[0]
                )

                current_progress = (
                    user_objective[1] or 0
                )

                already_completed = bool(
                    user_objective[2]
                )

            else:

                session.execute(
                    text(
                        """
                        INSERT INTO
                            esecurityin_user_daily_objectives
                        (
                            user_id,
                            objective_id,
                            objective_date,
                            progress,
                            completed,
                            completed_at
                        )
                        VALUES
                        (
                            :user_id,
                            :objective_id,
                            :objective_date,
                            0,
                            0,
                            NULL
                        )
                        """
                    ),
                    {
                        "user_id": user_id,
                        "objective_id": objective_id,
                        "objective_date": today,
                    },
                )

                result = session.execute(
                    text(
                        """
                        SELECT
                            id,
                            progress,
                            completed
                        FROM esecurityin_user_daily_objectives
                        WHERE user_id = :user_id
                          AND objective_id = :objective_id
                          AND objective_date = :objective_date
                        FOR UPDATE
                        """
                    ),
                    {
                        "user_id": user_id,
                        "objective_id": objective_id,
                        "objective_date": today,
                    },
                )

                user_objective = result.fetchone()

                user_objective_id = (
                    user_objective[0]
                )

                current_progress = 0

                already_completed = False

            if already_completed:
                continue

            # ---------------------------------------------
            # Calculate new progress
            # ---------------------------------------------

            if objective_type == "daily_solves":

                new_progress = (
                    current_progress + 1
                )

            elif objective_type == "daily_xp":

                new_progress = (
                    current_progress
                    + challenge_xp
                )

            else:

                new_progress = (
                    current_progress
                )

            new_progress = min(
                new_progress,
                target_value,
            )

            is_completed = (
                new_progress >= target_value
            )

            # ---------------------------------------------
            # Persist progress
            # ---------------------------------------------

            session.execute(
                text(
                    """
                    UPDATE
                        esecurityin_user_daily_objectives
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
                    "id": user_objective_id,
                },
            )

            # ---------------------------------------------
            # Objective completed
            # ---------------------------------------------

            if is_completed:

                newly_completed.append(
                    {
                        "id": objective_id,
                        "key": key,
                        "name": name,
                        "description": description,
                        "icon": icon,
                        "xp_reward": xp_reward,
                        "progress": new_progress,
                        "target_value": target_value,
                    }
                )

                print(
                    "🎯 Daily objective completed: "
                    f"{name}"
                )

                print(
                    "🎯 Daily objective reward: "
                    f"+{xp_reward} XP"
                )

        return newly_completed