"""Admin audit v1.4: add request context and details

Revision ID: ce33683facb1
Revises: 893e39e1240e
Create Date: 2026-01-15 22:32:35.396434

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ce33683facb1'
down_revision = '893e39e1240e'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table("admin_actions") as batch:
        batch.add_column(sa.Column("endpoint", sa.String(length=120), nullable=True))
        batch.add_column(sa.Column("method", sa.String(length=10), nullable=True))
        batch.add_column(sa.Column("path", sa.String(length=255), nullable=True))
        batch.add_column(sa.Column("details", sa.JSON(), nullable=True))
        batch.create_index("ix_admin_actions_endpoint", ["endpoint"])


def downgrade():
    with op.batch_alter_table("admin_actions") as batch:
        batch.drop_index("ix_admin_actions_endpoint")
        batch.drop_column("details")
        batch.drop_column("path")
        batch.drop_column("method")
        batch.drop_column("endpoint")
