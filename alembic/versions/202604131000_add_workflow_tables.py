"""add workflow tables

Revision ID: 202604131000
Revises: 202604091730
Create Date: 2026-04-13 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '202604131000'
down_revision: Union[str, None] = '202604091730'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'workflows',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('version', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True, server_default='draft'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_workflows_id', 'workflows', ['id'], unique=False)

    op.create_table(
        'workflow_nodes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('workflow_id', sa.Integer(), nullable=False),
        sa.Column('node_key', sa.String(length=36), nullable=False),
        sa.Column('node_type', sa.String(length=50), nullable=False),
        sa.Column('node_name', sa.String(length=100), nullable=False),
        sa.Column('pos_x', sa.Float(), nullable=True),
        sa.Column('pos_y', sa.Float(), nullable=True),
        sa.Column('config_json', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['workflow_id'], ['workflows.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('node_key')
    )
    op.create_index('ix_workflow_nodes_id', 'workflow_nodes', ['id'], unique=False)

    op.create_table(
        'workflow_edges',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('workflow_id', sa.Integer(), nullable=False),
        sa.Column('source_node_key', sa.String(length=36), nullable=False),
        sa.Column('target_node_key', sa.String(length=36), nullable=False),
        sa.Column('source_port', sa.Integer(), nullable=True),
        sa.Column('target_port', sa.Integer(), nullable=True),
        sa.Column('condition_json', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['workflow_id'], ['workflows.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_workflow_edges_id', 'workflow_edges', ['id'], unique=False)

    op.create_table(
        'workflow_runs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('workflow_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=True, server_default='pending'),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('trigger_type', sa.String(length=20), nullable=True, server_default='manual'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.ForeignKeyConstraint(['workflow_id'], ['workflows.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_workflow_runs_id', 'workflow_runs', ['id'], unique=False)

    op.create_table(
        'workflow_run_nodes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('run_id', sa.Integer(), nullable=False),
        sa.Column('node_key', sa.String(length=36), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=True, server_default='pending'),
        sa.Column('output', sa.Text(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['run_id'], ['workflow_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_workflow_run_nodes_id', 'workflow_run_nodes', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_workflow_run_nodes_id', table_name='workflow_run_nodes')
    op.drop_table('workflow_run_nodes')

    op.drop_index('ix_workflow_runs_id', table_name='workflow_runs')
    op.drop_table('workflow_runs')

    op.drop_index('ix_workflow_edges_id', table_name='workflow_edges')
    op.drop_table('workflow_edges')

    op.drop_index('ix_workflow_nodes_id', table_name='workflow_nodes')
    op.drop_table('workflow_nodes')

    op.drop_index('ix_workflows_id', table_name='workflows')
    op.drop_table('workflows')
