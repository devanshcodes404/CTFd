
"""Add daily objective unique constraint.

Revision ID: 87239919b615
Revises: c3a8f1d24b70
"""

from alembic import op
import sqlalchemy as sa


revision = "87239919b615"
down_revision = "c3a8f1d24b70"
branch_labels = None
depends_on = None

TABLE = "esecurityin_user_daily_objectives"
CONSTRAINT = "uq_esecurityin_user_daily_objective_date"
COLUMNS = ["user_id", "objective_id", "objective_date"]


def find_existing_unique(bind):
    """Find an existing unique constraint or index on these columns."""
    inspector = sa.inspect(bind)

    if not inspector.has_table(TABLE):
        return None

    for constraint in inspector.get_unique_constraints(TABLE):
        if (
            constraint.get("name") == CONSTRAINT
            or constraint.get("column_names") == COLUMNS
        ):
            return constraint.get("name") or CONSTRAINT

    for index in inspector.get_indexes(TABLE):
        if index.get("unique") and (
            index.get("name") == CONSTRAINT
            or index.get("column_names") == COLUMNS
        ):
            return index.get("name") or CONSTRAINT

    return None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # The plugin may not have created its table yet.
    if not inspector.has_table(TABLE):
        return

    # Avoid duplicating the constraint if it already exists.
    if find_existing_unique(bind) is None:
        op.create_unique_constraint(
            CONSTRAINT,
            TABLE,
            COLUMNS,
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table(TABLE):
        return

    existing = find_existing_unique(bind)

    # Only drop the specifically named constraint.
    if existing == CONSTRAINT:
        op.drop_constraint(
            CONSTRAINT,
            TABLE,
            type_="unique",
        )
