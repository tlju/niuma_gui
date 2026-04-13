"""modify system params table

Revision ID: 202604091220
Revises: 201ad17a7900
Create Date: 2026-04-09 12:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '202604091220'
down_revision: Union[str, None] = '201ad17a7900'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('''
        CREATE TABLE system_params_new (
            id INTEGER PRIMARY KEY,
            param_name VARCHAR(100) NOT NULL,
            param_code VARCHAR(100) UNIQUE NOT NULL,
            param_value TEXT,
            status VARCHAR(20) DEFAULT 'active',
            description TEXT
        )
    ''')
    
    op.execute('''
        INSERT INTO system_params_new (id, param_name, param_code, param_value, status, description)
        SELECT id, param_key, param_key, param_value, 'active', description
        FROM system_params
    ''')
    
    op.execute('DROP TABLE system_params')
    op.execute('ALTER TABLE system_params_new RENAME TO system_params')


def downgrade() -> None:
    op.execute('''
        CREATE TABLE system_params_new (
            id INTEGER PRIMARY KEY,
            param_key VARCHAR(100) UNIQUE NOT NULL,
            param_value TEXT,
            param_type VARCHAR(20) DEFAULT 'string',
            description TEXT
        )
    ''')
    
    op.execute('''
        INSERT INTO system_params_new (id, param_key, param_value, param_type, description)
        SELECT id, param_code, param_value, 'string', description
        FROM system_params
    ''')
    
    op.execute('DROP TABLE system_params')
    op.execute('ALTER TABLE system_params_new RENAME TO system_params')
