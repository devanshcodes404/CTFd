"""Add CyberRealm mission tables

Revision ID: cad2822dc674
Revises: 9c7e4d2a1f30
Create Date: 2026-09-06

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "cad2822dc674"
down_revision = "9c7e4d2a1f30"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "esecurityin_missions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "icon",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "mission_type",
            sa.String(length=20),
            nullable=False,
        ),
        sa.Column(
            "objective_type",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "target_value",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "xp_reward",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "active",
            sa.Boolean(),
            nullable=False,
        ),
        sa.Column("starts_at", sa.DateTime(), nullable=True),
        sa.Column("ends_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )

    op.create_index(
        "ix_esecurityin_missions_key",
        "esecurityin_missions",
        ["key"],
        unique=True,
    )

    op.create_index(
        "ix_esecurityin_missions_mission_type",
        "esecurityin_missions",
        ["mission_type"],
        unique=False,
    )

    op.create_table(
        "esecurityin_user_missions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("mission_id", sa.Integer(), nullable=False),
        sa.Column("period_key", sa.String(length=50), nullable=False),
        sa.Column(
            "progress",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "completed",
            sa.Boolean(),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["mission_id"],
            ["esecurityin_missions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),

    )

    op.create_index(
        "ix_esecurityin_user_missions_user_id",
        "esecurityin_user_missions",
        ["user_id"],
        unique=False,
    )

    op.create_index(
        "ix_esecurityin_user_missions_mission_id",
        "esecurityin_user_missions",
        ["mission_id"],
        unique=False,
    )

    op.create_index(
        "ix_esecurityin_user_missions_period_key",
        "esecurityin_user_missions",
        ["period_key"],
        unique=False,
    )


def downgrade():
    op.drop_index(
        "ix_esecurityin_user_missions_period_key",
        table_name="esecurityin_user_missions",
    )

    op.drop_index(
        "ix_esecurityin_user_missions_mission_id",
        table_name="esecurityin_user_missions",
    )

    op.drop_index(
        "ix_esecurityin_user_missions_user_id",
        table_name="esecurityin_user_missions",
    )

    op.drop_table("esecurityin_user_missions")

    op.drop_index(
        "ix_esecurityin_missions_mission_type",
        table_name="esecurityin_missions",
    )

    op.drop_index(
        "ix_esecurityin_missions_key",
        table_name="esecurityin_missions",
    )

    op.drop_table("esecurityin_missions")
