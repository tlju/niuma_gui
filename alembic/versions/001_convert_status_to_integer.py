"""convert status to integer

Revision ID: 202604091330
Revises: 202604091220
Create Date: 2026-04-09

"""
from alembic import op
import sqlalchemy as sa

revision = '202604091330'
down_revision = '202604091220'
branch_labels = None
depends_on = None

def upgrade():
    op.execute("ALTER TABLE system_params ADD COLUMN status_new INTEGER")
    op.execute("UPDATE system_params SET status_new = CASE WHEN status = 'active' THEN 1 ELSE 0 END")
    op.execute("ALTER TABLE system_params DROP COLUMN status")
    op.execute("ALTER TABLE system_params RENAME COLUMN status_new TO status")
    
    op.execute("ALTER TABLE users ADD COLUMN status_new INTEGER")
    op.execute("UPDATE users SET status_new = CASE WHEN status = 'active' THEN 1 WHEN status = 'inactive' THEN 0 WHEN status = 'locked' THEN 2 ELSE 1 END")
    op.execute("ALTER TABLE users DROP COLUMN status")
    op.execute("ALTER TABLE users RENAME COLUMN status_new TO status")

def downgrade():
    op.execute("ALTER TABLE system_params ADD COLUMN status_new VARCHAR(20)")
    op.execute("UPDATE system_params SET status_new = CASE WHEN status = 1 THEN 'active' ELSE 'inactive' END")
    op.execute("ALTER TABLE system_params DROP COLUMN status")
    op.execute("ALTER TABLE system_params RENAME COLUMN status_new TO status")
    
    op.execute("ALTER TABLE users ADD COLUMN status_new VARCHAR(20)")
    op.execute("UPDATE users SET status_new = CASE WHEN status = 1 THEN 'active' WHEN status = 0 THEN 'inactive' WHEN status = 2 THEN 'locked' ELSE 'active' END")
    op.execute("ALTER TABLE users DROP COLUMN status")
    op.execute("ALTER TABLE users RENAME COLUMN status_new TO status")
