from datetime import datetime, timezone

from CTFd.models import db
from ..models import UserXP


class XPService:

    XP_TABLE = {
        "easy": 50,
        "medium": 100,
        "hard": 200,
        "insane": 400
    }

    @classmethod
    def calculate_xp(cls, difficulty):
        return cls.XP_TABLE.get(difficulty.lower(), 50)

    @classmethod
    def level_from_xp(cls, xp):
        return (xp // 500) + 1

    @classmethod
    def get_or_create_user(cls, user_id):

        user = UserXP.query.filter_by(
            user_id=user_id
        ).first()

        if not user:
            user = UserXP(
                user_id=user_id,
                xp=0,
                level=1,
                streak=0,
                longest_streak=0,
                total_solves=0,
                last_solve_date=None
            )

            db.session.add(user)

        return user

    @classmethod
    def add_xp(cls, user_id, amount):

        user = cls.get_or_create_user(user_id)

        if user.xp is None:
            user.xp = 0

        if user.level is None:
            user.level = 1

        user.xp += amount
        user.level = cls.level_from_xp(user.xp)

        return user

    @classmethod
    def record_solve(cls, user_id):

        user = cls.get_or_create_user(user_id)

        today = datetime.now(timezone.utc).date()

        # First-ever solve
        if user.last_solve_date is None:
            user.streak = 1

        # Already solved something today
        elif user.last_solve_date == today:
            pass

        # Solved something yesterday
        elif (today - user.last_solve_date).days == 1:
            user.streak += 1

        # Streak was broken
        else:
            user.streak = 1

        # Update longest streak
        if user.streak > user.longest_streak:
            user.longest_streak = user.streak

        # Every successful challenge solve counts
        user.total_solves += 1

        # Remember the latest solve date
        user.last_solve_date = today

        return user