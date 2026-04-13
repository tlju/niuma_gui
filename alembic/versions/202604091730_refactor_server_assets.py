"""refactor server assets table

Revision ID: 202604091730
Revises: 202604091330
Create Date: 2026-04-09 17:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '202604091730'
down_revision: Union[str, None] = '202604091330'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('''
        CREATE TABLE server_assets_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            unit_name VARCHAR(100) NOT NULL,
            system_name VARCHAR(100) NOT NULL,
            ip VARCHAR(45),
            ipv6 VARCHAR(45),
            port INTEGER,
            host_name VARCHAR(100),
            username VARCHAR(100) NOT NULL,
            password_cipher VARCHAR(255) NOT NULL,
            notes TEXT,
            business_service VARCHAR(200),
            location VARCHAR(100),
            server_type VARCHAR(100),
            vip VARCHAR(200),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    op.execute('''
        INSERT INTO server_assets_new (id, unit_name, system_name, ip, port, host_name, username, password_cipher, created_at)
        SELECT id, name, name, ip, port, hostname, username, password_cipher, created_at
        FROM server_assets
    ''')
    
    op.execute('DROP TABLE server_assets')
    op.execute('ALTER TABLE server_assets_new RENAME TO server_assets')


def downgrade() -> None:
    op.execute('''
        CREATE TABLE server_assets_new (
            id INTEGER PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            hostname VARCHAR(255),
            ip VARCHAR(50) NOT NULL,
            port INTEGER DEFAULT 22,
            os_type VARCHAR(50),
            description TEXT,
            username VARCHAR(50),
            password_cipher VARCHAR(500),
            private_key_cipher VARCHAR(2000),
            auth_type VARCHAR(20) DEFAULT 'password',
            is_active BOOLEAN DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME
        )
    ''')
    
    op.execute('''
        INSERT INTO server_assets_new (id, name, hostname, ip, port, username, password_cipher, created_at)
        SELECT id, unit_name, host_name, ip, port, username, password_cipher, created_at
        FROM server_assets
    ''')
    
    op.execute('DROP TABLE server_assets')
    op.execute('ALTER TABLE server_assets_new RENAME TO server_assets')
