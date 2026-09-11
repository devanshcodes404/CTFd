from datetime import date
from flask import Blueprint, jsonify, request
from sqlalchemy import text

from CTFd.models import db
from CTFd.scoreboard import get_standings
from CTFd.utils.decorators import authed_only
from CTFd.utils.user import get_current_user

from .services.daily_objective_service import (
    DailyObjectiveService,
)
from .services.mission_service import MissionService
from .services.xp_service import XPService

api = Blueprint(
    "esecurityin_api",
    __name__,
    url_prefix="/api/v1/esecurityin",
)


# =========================================================
# HEALTH
# =========================================================

@api.route("/health", methods=["GET"])
def health():

    return jsonify(
        {
            "status": "online",
            "plugin": "eSecurityIn",
            "version": "1.0.0",
        }
    )


# =========================================================
# XP TEST
# =========================================================

@api.route("/xp/<difficulty>", methods=["GET"])
def xp_test(difficulty):

    xp = XPService.calculate_xp(
        difficulty
    )

    return jsonify(
        {
            "difficulty": difficulty,
            "xp": xp,
            "level_example":
                XPService.level_from_xp(xp),
        }
    )


# =========================================================
# SINGLE USER PROGRESSION
# =========================================================

@api.route("/user/<int:user_id>")
def get_user(user_id):

    user = XPService.get_or_create_user(user_id)

    return jsonify(
        {
            "user_id": user.user_id,
            "xp": user.xp,
            "level": user.level,
            "streak": user.streak,
            "longest_streak":
                user.longest_streak,
            "total_solves":
                user.total_solves,
            "last_solve_date": (
                user.last_solve_date.isoformat()
                if user.last_solve_date
                else None
            ),
        }
    )


# =========================================================
# CYBERREALM LEADERBOARD
#
# Returns CTFd standings + CyberRealm progression
# in ONE response.
# =========================================================

@api.route(
    "/leaderboard",
    methods=["GET"],
)
def get_leaderboard():

    standings = get_standings()

    if not standings:
        return jsonify(
            {
                "standings": [],
            }
        )

    # ---------------------------------------------------------
    # Collect CTFd account IDs
    # ---------------------------------------------------------

    account_ids = []

    for standing in standings:

        account_id = int(
            standing[0]
        )

        account_ids.append(
            account_id
        )

    account_ids = list(
        dict.fromkeys(account_ids)
    )

    if not account_ids:
        return jsonify(
            {
                "standings": [],
            }
        )

    # ---------------------------------------------------------
    # Load CyberRealm progression for all players
    # in ONE database query
    # ---------------------------------------------------------

    placeholders = ", ".join(
        f":user_{index}"
        for index in range(
            len(account_ids)
        )
    )

    params = {
        f"user_{index}": user_id
        for index, user_id in enumerate(
            account_ids
        )
    }

    result = db.session.execute(
        text(
            f"""
            SELECT
                user_id,
                xp,
                level,
                streak,
                longest_streak,
                total_solves,
                last_solve_date
            FROM user_xp
            WHERE user_id IN ({placeholders})
            """
        ),
        params,
    )

    progression_by_user = {}

    for row in result.fetchall():

        user_id = int(row[0])

        level = row[2] or 1

        progression_by_user[user_id] = {
            "xp": row[1] or 0,
            "level": level,
            "streak": row[3] or 0,
            "longest_streak": row[4] or 0,
            "total_solves": row[5] or 0,
            "last_solve_date": (
                row[6].isoformat()
                if row[6]
                else None
            ),
        }

    # ---------------------------------------------------------
    # Build combined leaderboard
    # ---------------------------------------------------------

    output = []

    for position, standing in enumerate(
        standings,
        start=1,
    ):

        # CTFd tuple structure:
        #
        # 0 = account_id
        # 1 = oauth_id
        # 2 = name
        # 3 = bracket_id
        # 4 = bracket_name
        # 5 = score

        account_id = int(
            standing[0]
        )

        name = (
            standing[2]
            if standing[2] is not None
            else "Unknown"
        )

        bracket_id = (
            standing[3]
            if standing[3] is not None
            else None
        )

        bracket_name = (
            standing[4]
            if standing[4] is not None
            else None
        )

        raw_score = (
            standing[5]
            if len(standing) > 5
            else 0
        )

        # Decimal -> int/float so JSON serialization
        # is predictable.
        score = int(
            raw_score or 0
        )

        progression = (
            progression_by_user.get(
                account_id,
                {
                    "xp": 0,
                    "level": 1,
                    "streak": 0,
                    "longest_streak": 0,
                    "total_solves": 0,
                    "last_solve_date": None,
                },
            )
        )

        level = (
            progression["level"]
        )

        output.append(
            {
                "pos": position,

                "account_id":
                    account_id,

                "account_url":
                    f"/users/{account_id}",

                "account_type":
                    "user",

                "name":
                    name,

                "bracket_id":
                    bracket_id,

                "bracket_name":
                    bracket_name,

                "score":
                    score,

                "xp":
                    progression["xp"],

                "level":
                    level,

                "rank":
                    get_player_rank(
                        level
                    ),

                "streak":
                    progression["streak"],

                "longest_streak":
                    progression[
                        "longest_streak"
                    ],

                "total_solves":
                    progression[
                        "total_solves"
                    ],

                "last_solve_date":
                    progression[
                        "last_solve_date"
                    ],
            }
        )

    return jsonify(
        {
            "standings": output,
        }
    )

# =========================================================
# PLAYER RANK
# =========================================================

def get_player_rank(level):

    if level >= 50:
        return "CYBER LEGEND"

    if level >= 30:
        return "SHADOW AGENT"

    if level >= 20:
        return "ELITE"

    if level >= 10:
        return "SPECIALIST"

    if level >= 5:
        return "OPERATIVE"

    return "RECRUIT"


# =========================================================
# USER ACHIEVEMENTS
# =========================================================

@api.route(
    "/user/<int:user_id>/achievements",
    methods=["GET"],
)
def get_user_achievements(user_id):

    result = db.session.execute(
        text(
            """
            SELECT
                a.id,
                a.`key`,
                a.name,
                a.description,
                a.icon,
                a.xp_reward,
                ua.unlocked_at
            FROM esecurityin_user_achievements AS ua
            JOIN esecurityin_achievements AS a
                ON a.id = ua.achievement_id
            WHERE ua.user_id = :user_id
            ORDER BY ua.unlocked_at DESC
            """
        ),
        {
            "user_id": user_id,
        },
    )


    achievements = []


    for row in result.fetchall():

        achievements.append(
            {
                "id": row[0],
                "key": row[1],
                "name": row[2],
                "description": row[3],
                "icon": row[4],
                "xp_reward": row[5],
                "unlocked_at": (
                    row[6].isoformat()
                    if row[6]
                    else None
                ),
            }
        )


    return jsonify(
        {
            "user_id": user_id,
            "count": len(achievements),
            "achievements": achievements,
        }
    )


# =========================================================
# ALL ACHIEVEMENTS
# =========================================================

@api.route(
    "/user/<int:user_id>/achievements/all",
    methods=["GET"],
)
def get_all_user_achievements(user_id):

    result = db.session.execute(
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
                a.requirement_value,
                CASE
                    WHEN ua.id IS NULL THEN 0
                    ELSE 1
                END AS unlocked,
                ua.unlocked_at
            FROM esecurityin_achievements AS a
            LEFT JOIN esecurityin_user_achievements AS ua
                ON ua.achievement_id = a.id
                AND ua.user_id = :user_id
            WHERE a.active = 1
            ORDER BY a.id ASC
            """
        ),
        {
            "user_id": user_id,
        },
    )


    achievements = []


    for row in result.fetchall():

        achievements.append(
            {
                "id": row[0],
                "key": row[1],
                "name": row[2],
                "description": row[3],
                "icon": row[4],
                "xp_reward": row[5],
                "requirement_type": row[6],
                "requirement_value": row[7],
                "unlocked": bool(row[8]),
                "unlocked_at": (
                    row[9].isoformat()
                    if row[9]
                    else None
                ),
            }
        )


    unlocked_count = sum(
        1
        for achievement in achievements
        if achievement["unlocked"]
    )


    return jsonify(
        {
            "user_id": user_id,
            "count": len(achievements),
            "unlocked_count":
                unlocked_count,
            "achievements":
                achievements,
        }
    )


# =========================================================
# PROFILE
# =========================================================

@api.route(
    "/profile/<int:user_id>",
    methods=["GET"],
)
def get_profile(user_id):

    user = XPService.get_or_create_user(user_id)

    result = db.session.execute(
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
                a.requirement_value,
                CASE
                    WHEN ua.id IS NULL THEN 0
                    ELSE 1
                END AS unlocked,
                ua.unlocked_at
            FROM esecurityin_achievements AS a
            LEFT JOIN esecurityin_user_achievements AS ua
                ON ua.achievement_id = a.id
                AND ua.user_id = :user_id
            WHERE a.active = 1
            ORDER BY a.id ASC
            """
        ),
        {
            "user_id": user_id,
        },
    )


    achievements = []


    for row in result.fetchall():

        achievements.append(
            {
                "id": row[0],
                "key": row[1],
                "name": row[2],
                "description": row[3],
                "icon": row[4],
                "xp_reward": row[5],
                "requirement_type": row[6],
                "requirement_value": row[7],
                "unlocked":
                    bool(row[8]),
                "unlocked_at": (
                    row[9].isoformat()
                    if row[9]
                    else None
                ),
            }
        )


    unlocked_count = sum(
        1
        for achievement in achievements
        if achievement["unlocked"]
    )


    total_achievements = len(achievements)

    return jsonify(
        {
            "user": {
                "id": user.user_id,
            },

            "progression": {
                "xp": user.xp,
                "level": user.level,
                "streak": user.streak,
                "longest_streak":
                    user.longest_streak,
                "total_solves":
                    user.total_solves,
                "last_solve_date": (
                    user.last_solve_date.isoformat()
                    if user.last_solve_date
                    else None
                ),
            },

            "achievements": {
                "unlocked":
                    unlocked_count,

                "total":
                    total_achievements,

                "items":
                    achievements,
            },
        }
    )


# =========================================================
# DAILY OBJECTIVES
# =========================================================

@api.route(
    "/user/<int:user_id>/daily-objectives",
    methods=["GET"],
)
def get_daily_objectives(user_id):

    objectives = DailyObjectiveService.get_today(user_id)


    return jsonify(
        {
            "user_id":
                user_id,

            "date":
                date.today().isoformat(),

            "objectives":
                objectives,
        }
    )

# =========================================================
# MISSIONS
# =========================================================

@api.route(
    "/missions",
    methods=["GET"],
)
@authed_only
def get_missions():
    user = get_current_user()

    mission_type = request.args.get(
        "type"
    )

    missions = MissionService.get_player_missions(
        user_id=user.id,
        mission_type=mission_type,
    )

    return jsonify(
        {
            "user_id": user.id,
            "missions": missions,
        }
    )

# =========================================================
# MANUAL XP
# =========================================================

@api.route(
    "/user/<int:user_id>/add/<int:xp>"
)
def add_xp(user_id, xp):

    user = XPService.add_xp(user_id, xp)


    return jsonify(
        {
            "user_id":
                user.user_id,

            "xp":
                user.xp,

            "level":
                user.level,
        }
    )