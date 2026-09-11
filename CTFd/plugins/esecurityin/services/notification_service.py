from CTFd.models import Notifications, db


class NotificationService:
    """
    Creates CyberRealm notifications using CTFd's
    native notifications system.

    Notifications are added to the current SQLAlchemy
    transaction. The caller is responsible for committing.
    """

    @staticmethod
    def _create(
        user_id,
        title,
        content,
    ):
        notification = Notifications(
            title=title,
            content=content,
            user_id=user_id,
            team_id=None,
        )

        db.session.add(notification)

        return notification

    @classmethod
    def xp_gained(
        cls,
        user_id,
        amount,
        challenge_name=None,
    ):
        if challenge_name:
            content = (
                f"**+{amount} XP** earned for solving "
                f"**{challenge_name}**."
            )
        else:
            content = f"**+{amount} XP** earned."

        return cls._create(
            user_id=user_id,
            title="⚡ XP Gained",
            content=content,
        )

    @classmethod
    def level_up(
        cls,
        user_id,
        level,
    ):
        return cls._create(
            user_id=user_id,
            title="👑 Level Up",
            content=(
                f"Congratulations! You reached "
                f"**Level {level}**."
            ),
        )

    @classmethod
    def achievement_unlocked(
        cls,
        user_id,
        achievement,
    ):
        name = achievement.get(
            "name",
            "Achievement",
        )

        description = achievement.get(
            "description",
            "",
        )

        reward = achievement.get(
            "xp_reward",
            0,
        )

        return cls._create(
            user_id=user_id,
            title="🏆 Achievement Unlocked",
            content=(
                f"**{name}**\n\n"
                f"{description}\n\n"
                f"**+{reward} XP**"
            ),
        )

    @classmethod
    def objective_completed(
        cls,
        user_id,
        objective,
    ):
        name = objective.get(
            "name",
            "Daily Objective",
        )

        description = objective.get(
            "description",
            "",
        )

        reward = objective.get(
            "xp_reward",
            0,
        )

        return cls._create(
            user_id=user_id,
            title="🎯 Objective Complete",
            content=(
                f"**{name}**\n\n"
                f"{description}\n\n"
                f"**+{reward} XP**"
            ),
        )
    @classmethod
    def mission_completed(
        cls,
        user_id,
        mission,
    ):
        name = mission.get(
            "name",
            "Mission",
        )

        description = mission.get(
            "description",
            "",
        )

        reward = mission.get(
            "xp_reward",
            0,
        )

        mission_type = mission.get(
            "mission_type",
            "special",
        )

        return cls._create(
            user_id=user_id,
            title="🚀 Mission Complete",
            content=(
                f"**{name}**\n\n"
                f"{description}\n\n"
                f"**{mission_type.title()} Mission**\n\n"
                f"**+{reward} XP**"
            ),
        )