from CTFd.models import Challenges

from .services.xp_service import XPService


def handle_solve(solve):

    print("🔥 eSecurityIn: handle_solve() CALLED")
    print(f"🔥 User ID: {solve.user_id}")
    print(f"🔥 Challenge ID: {solve.challenge_id}")

    challenge = Challenges.query.filter_by(
        id=solve.challenge_id
    ).first()

    if not challenge:
        print("❌ Challenge not found")
        return

    points = challenge.value or 0

    xp = max(10, points // 2)

    print(f"🔥 Challenge: {challenge.name}")
    print(f"🔥 Challenge points: {points}")
    print(f"🔥 XP to award: {xp}")

    # Award XP
    XPService.add_xp(
        solve.user_id,
        xp
    )

    print("🔥 XPService.add_xp() finished")

    # Record progression
    user = XPService.record_solve(
        solve.user_id
    )

    print(
        f"🔥 Streak: {user.streak}"
    )

    print(
        f"🔥 Longest streak: {user.longest_streak}"
    )

    print(
        f"🔥 Total solves: {user.total_solves}"
    )