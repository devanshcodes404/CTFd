from datetime import date, datetime, timezone

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

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
    def get_current_date(cls):
        """
        Return the current UTC calendar date.

        Mission periods must use the same timezone everywhere
        so API reads and solve processing cannot disagree.
        """

        return datetime.now(
            timezone.utc
        ).date()


    @classmethod
    def supports_row_locking(cls, session):
        """
        Return whether the current database supports SELECT ... FOR UPDATE.

        SQLite does not support row-level FOR UPDATE locking, so the
        development path remains compatible with it.
        """

        bind = session.get_bind()

        if bind is None:
            return False

        return (
            bind.dialect.name != "sqlite"
        )


    @classmethod
    def select_progress(
        cls,
        session,
        user_id,
        mission_id,
        period_key,
        for_update=False,
    ):
        """
        Load one mission progress row.

        On databases with row-level locking support, FOR UPDATE is
        used when requested to serialize concurrent progression updates.
        """

        lock_clause = ""

        if (
            for_update
            and cls.supports_row_locking(
                session
            )
        ):
            lock_clause = " FOR UPDATE"

        result = session.execute(
            text(
                f"""
                SELECT
                    id,
                    progress,
                    completed
                FROM esecurityin_user_missions
                WHERE user_id = :user_id
                  AND mission_id = :mission_id
                  AND period_key = :period_key
                {lock_clause}
                """
            ),
            {
                "user_id": user_id,
                "mission_id": mission_id,
                "period_key": period_key,
            },
        )

        return result.fetchone()


    @classmethod
    def create_progress_safely(
        cls,
        session,
        user_id,
        mission_id,
        period_key,
    ):
        """
        Create a mission progress row safely.

        The database uniqueness constraint is the final concurrency
        guard. A concurrent insert conflict is isolated to a savepoint,
        then the existing row is fetched and locked.
        """

        try:

            with session.begin_nested():

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

        except IntegrityError:

            pass

        return cls.select_progress(
            session=session,
            user_id=user_id,
            mission_id=mission_id,
            period_key=period_key,
            for_update=True,
        )


    @classmethod
    def seed_missions(cls):

        for definition in cls.MISSIONS:

            existing = (
                Mission.query
                .filter_by(
                    key=definition["key"]
                )
                .first()
            )

            if existing:
                continue

            mission = Mission(
                **definition
            )

            db.session.add(
                mission
            )

        db.session.commit()


    @classmethod
    def get_active_missions(
        cls,
        mission_type=None,
    ):

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
    def get_period_key(
        cls,
        mission_type,
        current_date=None,
    ):

        if current_date is None:
            current_date = cls.get_current_date()

        if mission_type == "daily":

            return current_date.isoformat()

        if mission_type == "weekly":

            year, week, _ = (
                current_date.isocalendar()
            )

            return (
                f"{year}-W{week:02d}"
            )

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

            current_date = (
                cls.get_current_date()
            )

        period_key = (
            cls.get_period_key(
                mission.mission_type,
                current_date,
            )
        )

        active_session = (
            session
            if session is not None
            else db.session
        )

        progress = (
            UserMission.query
            .filter_by(
                user_id=user_id,
                mission_id=mission.id,
                period_key=period_key,
            )
            .first()
        )

        if progress:

            return progress

        try:

            with active_session.begin_nested():

                progress = UserMission(
                    user_id=user_id,
                    mission_id=mission.id,
                    period_key=period_key,
                    progress=0,
                    completed=False,
                    completed_at=None,
                )

                active_session.add(
                    progress
                )

                active_session.flush()

        except IntegrityError:

            progress = (
                UserMission.query
                .filter_by(
                    user_id=user_id,
                    mission_id=mission.id,
                    period_key=period_key,
                )
                .first()
            )

            if progress:

                return progress

            raise

        return progress


    @classmethod
    def get_player_missions(
        cls,
        user_id,
        mission_type=None,
    ):

        missions = (
            cls.get_active_missions(
                mission_type=mission_type
            )
        )

        current_date = (
            cls.get_current_date()
        )

        progress_rows = (
            UserMission.query
            .filter_by(
                user_id=user_id,
            )
            .all()
        )

        progress_map = {}

        for progress in progress_rows:

            progress_map[
                (
                    progress.mission_id,
                    progress.period_key,
                )
            ] = progress

        result = []

        for mission in missions:

            period_key = (
                cls.get_period_key(
                    mission.mission_type,
                    current_date,
                )
            )

            progress = progress_map.get(
                (
                    mission.id,
                    period_key,
                )
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

            completed_at = (
                progress.completed_at.isoformat()
                if progress
                and progress.completed_at
                else None
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
                    "period_key": period_key,
                    "progress": current_progress,
                    "completed": completed,
                    "remaining": max(
                        0,
                        mission.target_value
                        - current_progress,
                    ),
                    "completed_at": completed_at,
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

        current_date = (
            cls.get_current_date()
        )

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

            period_key = (
                cls.get_period_key(
                    mission_type,
                    current_date,
                )
            )

            user_mission = (
                cls.select_progress(
                    session=session,
                    user_id=user_id,
                    mission_id=mission_id,
                    period_key=period_key,
                    for_update=True,
                )
            )

            if user_mission is None:

                user_mission = (
                    cls.create_progress_safely(
                        session=session,
                        user_id=user_id,
                        mission_id=mission_id,
                        period_key=period_key,
                    )
                )

            if user_mission is None:

                raise RuntimeError(
                    "Unable to create or retrieve "
                    "CyberRealm mission progress row."
                )

            (
                user_mission_id,
                current_progress,
                already_completed,
            ) = user_mission

            current_progress = (
                current_progress or 0
            )

            already_completed = bool(
                already_completed
            )

            if already_completed:

                continue

            if objective_type == "solves":

                new_progress = (
                    current_progress + 1
                )

            elif objective_type == "xp":

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

            session.execute(
                text(
                    """
                    UPDATE
                        esecurityin_user_missions
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