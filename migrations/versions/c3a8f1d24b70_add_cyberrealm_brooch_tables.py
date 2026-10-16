"""Add CyberRealm brooch tables

Revision ID: c3a8f1d24b70
Revises: 8f31c6a2e947
Create Date: 2026-09-17

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c3a8f1d24b70"
down_revision = "8f31c6a2e947"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "esecurityin_brooches",
        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
        ),
        sa.Column(
            "key",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "name",
            sa.String(length=150),
            nullable=False,
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "asset_key",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "requirement_type",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "requirement_value",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
        sa.Column(
            "requirement_key",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "sort_order",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.UniqueConstraint(
            "key",
            name="uq_esecurityin_brooch_key",
        ),
        sa.Index(
            "ix_esecurityin_brooches_key",
            "key",
        ),
    )

    op.create_table(
        "esecurityin_user_brooches",
        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "brooch_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "unlocked_at",
            sa.DateTime(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["brooch_id"],
            ["esecurityin_brooches.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "user_id",
            "brooch_id",
            name="uq_esecurityin_user_brooch",
        ),
        sa.Index(
            "ix_esecurityin_user_brooches_user_id",
            "user_id",
        ),
        sa.Index(
            "ix_esecurityin_user_brooches_brooch_id",
            "brooch_id",
        ),
    )


def downgrade():
    op.drop_table("esecurityin_user_brooches")
    op.drop_table("esecurityin_brooches")