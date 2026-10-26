"""Add the missing user foreign key to UserXP.

Revision ID: f28c4d9a6b13
Revises: b7c4d29a1f60
Create Date: 2026-10-24
"""

from alembic import op
import sqlalchemy as sa


revision = "f28c4d9a6b13"
down_revision = "b7c4d29a1f60"
branch_labels = None
depends_on = None


TABLE = "user_xp"
CONSTRAINT = "fk_user_xp_user_id_users"


def _expected_foreign_key(foreign_key):
    return (
        foreign_key.get("constrained_columns") == ["user_id"]
        and foreign_key.get("referred_table") == "users"
        and foreign_key.get("referred_columns") == ["id"]
        and ((foreign_key.get("options") or {}).get("ondelete") or "").upper()
        == "CASCADE"
    )


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table(TABLE) or not inspector.has_table("users"):
        raise RuntimeError(
            "Cannot add the UserXP user foreign key: expected both "
            "'user_xp' and 'users' tables to exist."
        )

    orphan_count = bind.execute(
        sa.text(
            """
            SELECT COUNT(*)
            FROM user_xp AS xp
            LEFT JOIN users AS u ON u.id = xp.user_id
            WHERE u.id IS NULL
            """
        )
    ).scalar_one()
    if orphan_count:
        orphan_ids = [
            row[0]
            for row in bind.execute(
                sa.text(
                    """
                    SELECT xp.user_id
                    FROM user_xp AS xp
                    LEFT JOIN users AS u ON u.id = xp.user_id
                    WHERE u.id IS NULL
                    ORDER BY xp.user_id
                    LIMIT 10
                    """
                )
            )
        ]
        raise RuntimeError(
            f"Cannot add the UserXP user foreign key: found {orphan_count} "
            f"user_xp row(s) with no matching users.id (sample user_id values: "
            f"{orphan_ids}). No rows were deleted; review and repair these "
            "records before retrying this migration."
        )

    foreign_keys = inspector.get_foreign_keys(TABLE)
    if any(_expected_foreign_key(foreign_key) for foreign_key in foreign_keys):
        return

    conflicting_foreign_keys = [
        foreign_key
        for foreign_key in foreign_keys
        if "user_id" in (foreign_key.get("constrained_columns") or [])
    ]
    if conflicting_foreign_keys:
        raise RuntimeError(
            "Cannot add the UserXP user foreign key because user_xp.user_id "
            "already has a different foreign-key constraint. Review and "
            "resolve that constraint before retrying this migration."
        )

    op.create_foreign_key(
        CONSTRAINT,
        TABLE,
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade():
    foreign_keys = sa.inspect(op.get_bind()).get_foreign_keys(TABLE)
    if any(
        foreign_key.get("name") == CONSTRAINT
        for foreign_key in foreign_keys
    ):
        op.drop_constraint(CONSTRAINT, TABLE, type_="foreignkey")
