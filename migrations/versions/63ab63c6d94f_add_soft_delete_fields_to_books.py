"""Add soft delete fields to books

Revision ID: 63ab63c6d94f
Revises: 0ccb05fa05e8
Create Date: 2026-01-12
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "63ab63c6d94f"
down_revision = "0ccb05fa05e8"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("books", schema=None) as batch_op:
        batch_op.add_column(sa.Column("deleted_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("deleted_by_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_books_deleted_at", ["deleted_at"], unique=False)
        batch_op.create_index("ix_books_deleted_by_id", ["deleted_by_id"], unique=False)
        batch_op.create_foreign_key(
            "fk_books_deleted_by_id_users",
            "users",
            ["deleted_by_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade():
    with op.batch_alter_table("books", schema=None) as batch_op:
        batch_op.drop_constraint("fk_books_deleted_by_id_users", type_="foreignkey")
        batch_op.drop_index("ix_books_deleted_by_id")
        batch_op.drop_index("ix_books_deleted_at")
        batch_op.drop_column("deleted_by_id")
        batch_op.drop_column("deleted_at")
