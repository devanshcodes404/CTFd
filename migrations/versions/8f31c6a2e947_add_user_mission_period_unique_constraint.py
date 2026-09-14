"""Add unique constraint to CyberRealm user missions

Revision ID: 8f31c6a2e947
Revises: cad2822dc674
Create Date: 2026-09-14

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "8f31c6a2e947"
down_revision = "cad2822dc674"
branch_labels = None
depends_on = None


def upgrade():
    op.create_unique_constraint(
        "uq_esecurityin_user_mission_period",
        "esecurityin_user_missions",
        [
            "user_id",
            "mission_id",
            "period_key",
        ],
    )


def downgrade():
    op.drop_constraint(
        "uq_esecurityin_user_mission_period",
        "esecurityin_user_missions",
        type_="unique",
    )