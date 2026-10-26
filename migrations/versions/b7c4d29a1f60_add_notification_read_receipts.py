"""Add per-user notification read receipts

Revision ID: b7c4d29a1f60
Revises: d8b5f2a1c907
Create Date: 2026-10-24

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b7c4d29a1f60"
down_revision = "d8b5f2a1c907"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "notification_read_receipts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("notification_id", sa.Integer(), nullable=False),
        sa.Column("read_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["notification_id"], ["notifications.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "notification_id", name="uq_notification_read_receipt"
        ),
    )
    op.create_index(
        "ix_notification_read_receipts_user_id",
        "notification_read_receipts",
        ["user_id"],
    )
    op.create_index(
        "ix_notification_read_receipts_notification_id",
        "notification_read_receipts",
        ["notification_id"],
    )


def downgrade():
    op.drop_index(
        "ix_notification_read_receipts_notification_id",
        table_name="notification_read_receipts",
    )
    op.drop_index(
        "ix_notification_read_receipts_user_id",
        table_name="notification_read_receipts",
    )
    op.drop_table("notification_read_receipts")
