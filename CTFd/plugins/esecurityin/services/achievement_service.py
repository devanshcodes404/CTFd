from sqlalchemy import text

from CTFd.models import db

from ..models import Achievement, UserAchievement


class AchievementService:

    ACHIEVEMENTS = [
        {
            "key": "first_blood",
            "name": "First Blood",
            "description": "Solve your first challenge.",
            "icon": "🎯",
            "xp_reward": 25,
            "requirement_type": "total_solves",
            "requirement_value": 1,
        },
        {
            "key": "getting_started",
            "name": "Getting Started",
            "description": "Solve 3 challenges.",
            "icon": "🔥",
            "xp_reward": 50,
            "requirement_type": "total_solves",
            "requirement_value": 3,
        },
        {
            "key": "on_fire",
            "name": "On Fire",
            "description": "Reach a 3-day solving streak.",
            "icon": "⚡",
            "xp_reward": 100,
            "requirement_type": "streak",
            "requirement_value": 3,
        },
        {
            "key": "hacker",
            "name": "Hacker",
            "description": "Solve 10 challenges.",
            "icon": "💀",
            "xp_reward": 150,
            "requirement_type": "total_solves",
            "requirement_value": 10,
        },
        {
            "key": "specialist",
            "name": "Specialist",
            "description": "Reach Level 5.",
            "icon": "🧠",
            "xp_reward": 200,
            "requirement_type": "level",
            "requirement_value": 5,
        },
        {
            "key": "elite_hacker",
            "name": "Elite Hacker",
            "description": "Reach Level 10.",
            "icon": "👑",
            "xp_reward": 500,
            "requirement_type": "level",
            "requirement_value": 10,
        },
    ]

    @classmethod
    def seed_achievements(cls):
        for definition in cls.ACHIEVEMENTS:
            existing = Achievement.query.filter_by(
                key=definition["key"]
            ).first()

            if not existing:
                achievement = Achievement(**definition)
                db.session.add(achievement)

        db.session.commit()

    @classmethod
    def process_unlocks(cls, session, user_id):
        """
        Check all achievement requirements for a player.

        This function uses the existing SQLAlchemy transaction/session
        supplied by the solve event. It does not commit independently.
        """

        newly_unlocked = []

        # Allow achievement rewards to unlock another achievement
        # during the same solve if the reward crosses a threshold.
        while True:

            # -----------------------------------------------------
            # Read current player progression
            # -----------------------------------------------------

            result = session.execute(
                text(
                    """
                    SELECT
                        xp,
                        level,
                        streak,
                        total_solves
                    FROM user_xp
                    WHERE user_id = :user_id
                    FOR UPDATE
                    """
                ),
                {
                    "user_id": user_id,
                },
            )

            user = result.fetchone()

            if not user:
                return newly_unlocked

            current_xp = user[0] or 0
            current_level = user[1] or 1
            current_streak = user[2] or 0
            current_total_solves = user[3] or 0

            # -----------------------------------------------------
            # Find achievements not yet unlocked
            # -----------------------------------------------------

            result = session.execute(
                text(
                    """
                    SELECT
                        a.id,
                        a.`key`,
                        a.name,
                        a.description,
                        a.icon,
                        a.xp_reward,
                        a.requirement_type,
                        a.requirement_value
                    FROM esecurityin_achievements AS a
                    LEFT JOIN esecurityin_user_achievements AS ua
                        ON ua.achievement_id = a.id
                        AND ua.user_id = :user_id
                    WHERE a.active = 1
                      AND ua.id IS NULL
                    ORDER BY a.id ASC
                    """
                ),
                {
                    "user_id": user_id,
                },
            )

            achievements = result.fetchall()

            reward_xp = 0

            for achievement in achievements:

                achievement_id = achievement[0]
                key = achievement[1]
                name = achievement[2]
                description = achievement[3]
                icon = achievement[4]
                xp_reward = achievement[5] or 0
                requirement_type = achievement[6]
                requirement_value = achievement[7]

                requirement_met = False

                if requirement_type == "total_solves":
                    requirement_met = (
                        current_total_solves
                        >= requirement_value
                    )

                elif requirement_type == "streak":
                    requirement_met = (
                        current_streak
                        >= requirement_value
                    )

                elif requirement_type == "level":
                    requirement_met = (
                        current_level
                        >= requirement_value
                    )

                if not requirement_met:
                    continue

                # -------------------------------------------------
                # Unlock achievement
                # -------------------------------------------------

                session.execute(
                    text(
                        """
                        INSERT INTO esecurityin_user_achievements
                        (
                            user_id,
                            achievement_id,
                            unlocked_at
                        )
                        VALUES
                        (
                            :user_id,
                            :achievement_id,
                            CURRENT_TIMESTAMP(6)
                        )
                        """
                    ),
                    {
                        "user_id": user_id,
                        "achievement_id": achievement_id,
                    },
                )

                newly_unlocked.append(
                    {
                        "id": achievement_id,
                        "key": key,
                        "name": name,
                        "description": description,
                        "icon": icon,
                        "xp_reward": xp_reward,
                    }
                )

                reward_xp += xp_reward

                print(
                    f"🏆 Achievement unlocked: {name}"
                )

                print(
                    f"🏆 Reward: +{xp_reward} XP"
                )

            # Nothing new unlocked → stop.
            if reward_xp == 0:
                break

            # -----------------------------------------------------
            # Apply achievement XP rewards
            # -----------------------------------------------------

            new_xp = current_xp + reward_xp
            new_level = (new_xp // 500) + 1

            session.execute(
                text(
                    """
                    UPDATE user_xp
                    SET
                        xp = :xp,
                        level = :level
                    WHERE user_id = :user_id
                    """
                ),
                {
                    "xp": new_xp,
                    "level": new_level,
                    "user_id": user_id,
                },
            )

            print(
                f"🏆 Achievement XP: "
                f"{current_xp} → {new_xp}"
            )

            print(
                f"🏆 Achievement level: "
                f"{current_level} → {new_level}"
            )

        return newly_unlocked