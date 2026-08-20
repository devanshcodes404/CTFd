from datetime import date, timedelta

from flask import Blueprint, render_template
from sqlalchemy import event, text
from sqlalchemy.orm import Session

from CTFd.models import Solves, db
from CTFd.utils.decorators import authed_only
from CTFd.utils.user import get_current_user

from .api import api
from .services.achievement_service import AchievementService
from .services.daily_objective_service import DailyObjectiveService


def load(app):
    bp = Blueprint(
        "esecurityin",
        __name__,
        template_folder="templates",
        static_folder="assets",
        url_prefix="/esecurityin",
    )

    @bp.route("/ping")
    def ping():
        return {
            "status": "success",
            "message": "eSecurityIn plugin loaded successfully!",
        }

    @app.route("/dashboard", methods=["GET"])
    @authed_only
    def cyberrealm_dashboard():
        user = get_current_user()

        return render_template(
            "dashboard.html",
            user=user,
        )

    app.register_blueprint(bp)
    app.register_blueprint(api)

    # Create plugin tables.
    db.create_all()

    # Seed static definitions.
    AchievementService.seed_achievements()
    DailyObjectiveService.seed_objectives()


@event.listens_for(Session, "before_flush")
def collect_new_solves(session, flush_context, instances):
    """
    Collect newly created CTFd solves before SQLAlchemy flushes them.
    """

    if "esecurityin_solves" not in session.info:
        session.info["esecurityin_solves"] = []

    for obj in session.new:
        if isinstance(obj, Solves):
            session.info["esecurityin_solves"].append(
                {
                    "user_id": obj.user_id,
                    "challenge_id": obj.challenge_id,
                }
            )


@event.listens_for(Session, "after_flush_postexec")
def award_xp_after_flush(session, flush_context):
    """
    Process newly created CTFd solves after the solve has been flushed.

    Progression handled inside the same transaction:

    - Challenge XP
    - Level
    - Streak
    - Longest streak
    - Total solves
    - Daily objectives
    - Daily-objective XP
    - Achievements
    """

    solves = session.info.pop(
        "esecurityin_solves",
        [],
    )

    if not solves:
        return

    for solve in solves:

        user_id = solve["user_id"]
        challenge_id = solve["challenge_id"]

        print("🔥🔥 eSecurityIn XP EVENT 🔥🔥")
        print(f"🔥 User ID: {user_id}")
        print(f"🔥 Challenge ID: {challenge_id}")

        # ---------------------------------------------------------
        # 1. Get challenge points
        # ---------------------------------------------------------

        result = session.execute(
            text(
                """
                SELECT value
                FROM challenges
                WHERE id = :challenge_id
                """
            ),
            {
                "challenge_id": challenge_id,
            },
        )

        challenge = result.fetchone()

        if not challenge:
            print("❌ Challenge not found")
            continue

        points = challenge[0] or 0

        # Current eSecurityIn rule:
        # 100 CTF points = 50 XP
        xp = max(
            10,
            points // 2,
        )

        print(
            f"🔥 Challenge points: {points}"
        )
        print(
            f"🔥 XP to award: {xp}"
        )

        # ---------------------------------------------------------
        # 2. Get existing UserXP row
        # ---------------------------------------------------------

        result = session.execute(
            text(
                """
                SELECT
                    xp,
                    level,
                    streak,
                    longest_streak,
                    total_solves,
                    last_solve_date
                FROM user_xp
                WHERE user_id = :user_id
                FOR UPDATE
                """
            ),
            {
                "user_id": user_id,
            },
        )

        user_xp = result.fetchone()

        today = date.today()

        # ---------------------------------------------------------
        # 3. Existing player
        # ---------------------------------------------------------

        if user_xp:

            current_xp = user_xp[0] or 0
            current_level = user_xp[1] or 1
            current_streak = user_xp[2] or 0
            current_longest_streak = user_xp[3] or 0
            current_total_solves = user_xp[4] or 0
            last_solve_date = user_xp[5]

            # XP
            new_xp = current_xp + xp

            # Level
            new_level = (
                new_xp // 500
            ) + 1

            # -----------------------------------------------------
            # Streak
            # -----------------------------------------------------

            if last_solve_date is None:

                new_streak = 1

            elif last_solve_date == today:

                new_streak = current_streak

            elif (
                last_solve_date
                == today - timedelta(days=1)
            ):

                new_streak = current_streak + 1

            else:

                new_streak = 1

            # Longest streak
            new_longest_streak = max(
                current_longest_streak,
                new_streak,
            )

            # Total solves
            new_total_solves = (
                current_total_solves + 1
            )

            # -----------------------------------------------------
            # 4. Persist challenge progression
            # -----------------------------------------------------

            session.execute(
                text(
                    """
                    UPDATE user_xp
                    SET
                        xp = :xp,
                        level = :level,
                        streak = :streak,
                        longest_streak = :longest_streak,
                        total_solves = :total_solves,
                        last_solve_date = :last_solve_date
                    WHERE user_id = :user_id
                    """
                ),
                {
                    "xp": new_xp,
                    "level": new_level,
                    "streak": new_streak,
                    "longest_streak": new_longest_streak,
                    "total_solves": new_total_solves,
                    "last_solve_date": today,
                    "user_id": user_id,
                },
            )

            print(
                f"🔥 XP: "
                f"{current_xp} → {new_xp}"
            )

            print(
                f"🔥 Level: "
                f"{current_level} → {new_level}"
            )

            print(
                f"🔥 Streak: "
                f"{current_streak} → {new_streak}"
            )

            print(
                f"🔥 Longest streak: "
                f"{current_longest_streak} → "
                f"{new_longest_streak}"
            )

            print(
                f"🔥 Total solves: "
                f"{current_total_solves} → "
                f"{new_total_solves}"
            )

        # ---------------------------------------------------------
        # 5. First solve / no UserXP row
        # ---------------------------------------------------------

        else:

            new_xp = xp

            new_level = (
                new_xp // 500
            ) + 1

            new_streak = 1
            new_longest_streak = 1
            new_total_solves = 1

            session.execute(
                text(
                    """
                    INSERT INTO user_xp
                    (
                        user_id,
                        xp,
                        level,
                        streak,
                        longest_streak,
                        total_solves,
                        last_solve_date
                    )
                    VALUES
                    (
                        :user_id,
                        :xp,
                        :level,
                        :streak,
                        :longest_streak,
                        :total_solves,
                        :last_solve_date
                    )
                    """
                ),
                {
                    "user_id": user_id,
                    "xp": new_xp,
                    "level": new_level,
                    "streak": new_streak,
                    "longest_streak": new_longest_streak,
                    "total_solves": new_total_solves,
                    "last_solve_date": today,
                },
            )

            print(
                f"🔥 Created UserXP for user {user_id}"
            )

            print(
                f"🔥 XP: {new_xp}"
            )

            print(
                f"🔥 Level: {new_level}"
            )

            print(
                f"🔥 Streak: {new_streak}"
            )

            print(
                f"🔥 Longest streak: "
                f"{new_longest_streak}"
            )

            print(
                f"🔥 Total solves: "
                f"{new_total_solves}"
            )

        # ---------------------------------------------------------
        # 6. Daily objectives
        # ---------------------------------------------------------

        completed_objectives = (
            DailyObjectiveService.process_solve(
                session=session,
                user_id=user_id,
                challenge_xp=xp,
            )
        )

        # ---------------------------------------------------------
        # 7. Award daily-objective XP
        # ---------------------------------------------------------

        objective_reward_xp = sum(
            objective["xp_reward"]
            for objective in completed_objectives
        )

        if objective_reward_xp > 0:

            result = session.execute(
                text(
                    """
                    SELECT xp
                    FROM user_xp
                    WHERE user_id = :user_id
                    FOR UPDATE
                    """
                ),
                {
                    "user_id": user_id,
                },
            )

            current_user_xp = (
                result.fetchone()
            )

            if current_user_xp:

                current_xp = (
                    current_user_xp[0] or 0
                )

                new_xp = (
                    current_xp
                    + objective_reward_xp
                )

                new_level = (
                    new_xp // 500
                ) + 1

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
                    "🎯 Daily objective XP: "
                    f"{current_xp} → {new_xp}"
                )

                print(
                    "🎯 Daily objective level: "
                    f"{new_level}"
                )

        # ---------------------------------------------------------
        # 8. Log completed objectives
        # ---------------------------------------------------------

        for objective in completed_objectives:

            print(
                "🎯 Daily objective completed: "
                f"{objective['name']}"
            )

            print(
                "🎯 Daily objective reward: "
                f"+{objective['xp_reward']} XP"
            )

        # ---------------------------------------------------------
        # 9. Achievements
        # ---------------------------------------------------------

        unlocked_achievements = (
            AchievementService.process_unlocks(
                session,
                user_id,
            )
        )

        for achievement in unlocked_achievements:

            print(
                "🏆 eSecurityIn unlocked: "
                f"{achievement['name']}"
            )