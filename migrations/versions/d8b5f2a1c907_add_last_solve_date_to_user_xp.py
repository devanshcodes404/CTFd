"""Add last solve date to UserXP.

Revision ID: d8b5f2a1c907
Revises: 87239919b615
Create Date: 2026-10-22

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "d8b5f2a1c907"
down_revision = "87239919b615"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "user_xp",
        sa.Column("last_solve_date", sa.Date(), nullable=True),
    )


def downgrade():
    op.drop_column("user_xp", "last_solve_date")
