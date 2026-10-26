from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from CTFd.models import db


class BroochService:
    BROOCHES = [
        {
            "key": "first_breach",
            "name": "First Breach",
            "description": "Complete your first successful breach.",
            "asset_key": "first_breach",
            "requirement_type": "achievement",
            "requirement_value": 1,
            "requirement_key": "first_blood",
            "active": True,
            "sort_order": 1,
        },
        {
            "key": "breach_runner",
            "name": "Breach Runner",
            "description": "Complete the Breach Runner mission.",
            "asset_key": "breach_runner",
            "requirement_type": "mission",
            "requirement_value": 1,
            "requirement_key": "daily_breach_runner",
            "active": True,
            "sort_order": 2,
        },
        {
            "key": "elite_operator",
            "name": "Elite Operator",
            "description": "Reach the Elite Operator achievement.",
            "asset_key": "elite_operator",
            "requirement_type": "achievement",
            "requirement_value": 1,
            "requirement_key": "elite_operator",
            "active": True,
            "sort_order": 3,
        },
        {
            "key": "crypto_specialist",
            "name": "Crypto Specialist",
            "description": "Master the cryptography challenge path.",
            "asset_key": "crypto_specialist",
            "requirement_type": "category_solves",
            "requirement_value": 5,
            "requirement_key": "crypto",
            "active": False,
            "sort_order": 4,
        },
        {
            "key": "web_defender",
            "name": "Web Defender",
            "description": "Master the web security challenge path.",
            "asset_key": "web_defender",
            "requirement_type": "category_solves",
            "requirement_value": 5,
            "requirement_key": "web",
            "active": False,
            "sort_order": 5,
        },
        {
            "key": "xp_hunter",
            "name": "XP Hunter",
            "description": "Reach the XP Hunter achievement.",
            "asset_key": "xp_hunter",
            "requirement_type": "achievement",
            "requirement_value": 1,
            "requirement_key": "xp_hunter",
            "active": True,
            "sort_order": 6,
        },
        {
            "key": "mission_commander",
            "name": "Mission Commander",
            "description": "Reach the Mission Commander achievement.",
            "asset_key": "mission_commander",
            "requirement_type": "achievement",
            "requirement_value": 1,
            "requirement_key": "mission_commander",
            "active": True,
            "sort_order": 7,
        },
        {
            "key": "stage_master",
            "name": "Stage Master",
            "description": "Complete a CyberRealm progression stage.",
            "asset_key": "stage_master",
            "requirement_type": "stage",
            "requirement_value": 1,
            "requirement_key": "stage_1",
            "active": False,
            "sort_order": 8,
        },
    ]

    @classmethod
    def seed_brooches(cls):
        from ..models import Brooch

        for definition in cls.BROOCHES:
            existing = (
                Brooch.query
                .filter_by(
                    key=definition["key"]
                )
                .first()
            )

            if existing:
                continue

            brooch = Brooch(
                **definition
            )

            db.session.add(brooch)

        db.session.commit()

    @classmethod
    def get_player_brooches(
        cls,
        user_id,
    ):
        result = db.session.execute(
            text(
                """
                SELECT
                    b.id,
                    b.`key`,
                    b.name,
                    b.description,
                    b.asset_key,
                    b.requirement_type,
                    b.requirement_value,
                    b.requirement_key,
                    b.active,
                    ub.unlocked_at
                FROM esecurityin_brooches AS b
                LEFT JOIN esecurityin_user_brooches AS ub
                    ON ub.brooch_id = b.id
                    AND ub.user_id = :user_id
                ORDER BY
                    b.sort_order ASC,
                    b.id ASC
                """
            ),
            {
                "user_id": user_id,
            },
        )

        brooches = []

        for row in result.fetchall():
            (
                brooch_id,
                key,
                name,
                description,
                asset_key,
                requirement_type,
                requirement_value,
                requirement_key,
                active,
                unlocked_at,
            ) = row

            unlocked = unlocked_at is not None

            if requirement_type in (
                "achievement",
                "mission",
            ):
                progress = (
                    requirement_value
                    if unlocked
                    else 0
                )
            else:
                progress = 0

            brooches.append(
                {
                    "id": brooch_id,
                    "key": key,
                    "name": name,
                    "description": description,
                    "asset_key": asset_key,
                    "requirement_type": requirement_type,
                    "requirement_value": requirement_value,
                    "requirement_key": requirement_key,
                    "active": bool(active),
                    "unlocked": unlocked,
                    "progress": progress,
                    "remaining": max(
                        0,
                        requirement_value - progress,
                    ),
                    "unlocked_at": (
                        unlocked_at.isoformat()
                        if unlocked_at
                        else None
                    ),
                }
            )

        return brooches

    @classmethod
    def process_unlocks(cls, session, user_id):
        """
        Unlock eligible CyberRealm brooches for a player.

        This is intentionally idempotent. Existing UserBrooch
        records are ignored, and the database uniqueness constraint
        protects against duplicate unlocks.
        """

        newly_unlocked = []

        result = session.execute(
            text(
                """
                SELECT
                    id,
                    `key`,
                    name,
                    description,
                    asset_key,
                    requirement_type,
                    requirement_value,
                    requirement_key
                FROM esecurityin_brooches
                WHERE active = 1
                ORDER BY sort_order ASC, id ASC
                """
            )
        )

        brooches = result.fetchall()

        for brooch in brooches:

            (
                brooch_id,
                key,
                name,
                description,
                asset_key,
                requirement_type,
                requirement_value,
                requirement_key,
            ) = brooch

            existing = session.execute(
                text(
                    """
                    SELECT id
                    FROM esecurityin_user_brooches
                    WHERE user_id = :user_id
                      AND brooch_id = :brooch_id
                    LIMIT 1
                    """
                ),
                {
                    "user_id": user_id,
                    "brooch_id": brooch_id,
                },
            ).fetchone()

            if existing:
                continue

            requirement_met = False

            if requirement_type == "achievement":

                achievement = session.execute(
                    text(
                        """
                        SELECT ua.id
                        FROM esecurityin_user_achievements AS ua
                        INNER JOIN esecurityin_achievements AS a
                            ON a.id = ua.achievement_id
                        WHERE ua.user_id = :user_id
                          AND a.key = :requirement_key
                        LIMIT 1
                        """
                    ),
                    {
                        "user_id": user_id,
                        "requirement_key": requirement_key,
                    },
                ).fetchone()

                requirement_met = achievement is not None

            elif requirement_type == "mission":

                mission = session.execute(
                    text(
                        """
                        SELECT um.id
                        FROM esecurityin_user_missions AS um
                        INNER JOIN esecurityin_missions AS m
                            ON m.id = um.mission_id
                        WHERE um.user_id = :user_id
                          AND m.key = :requirement_key
                          AND um.completed = 1
                        LIMIT 1
                        """
                    ),
                    {
                        "user_id": user_id,
                        "requirement_key": requirement_key,
                    },
                ).fetchone()

                requirement_met = mission is not None

            if not requirement_met:
                continue

            unlocked_at = datetime.now(
                timezone.utc
            ).replace(
                tzinfo=None
            )

            try:
                with session.begin_nested():

                    session.execute(
                        text(
                            """
                            INSERT INTO esecurityin_user_brooches
                            (
                                user_id,
                                brooch_id,
                                unlocked_at
                            )
                            VALUES
                            (
                                :user_id,
                                :brooch_id,
                                :unlocked_at
                            )
                            """
                        ),
                        {
                            "user_id": user_id,
                            "brooch_id": brooch_id,
                            "unlocked_at": unlocked_at,
                        },
                    )

            except IntegrityError as error:
                if (
                    not getattr(error.orig, "args", ())
                    or error.orig.args[0] != 1062
                ):
                    raise
                continue

            newly_unlocked.append(
                {
                    "id": brooch_id,
                    "key": key,
                    "name": name,
                    "description": description,
                    "asset_key": asset_key,
                    "requirement_type": requirement_type,
                    "requirement_value": requirement_value,
                    "requirement_key": requirement_key,
                }
            )

            print(
                f"📌 Brooch unlocked: {name}"
            )

        return newly_unlocked