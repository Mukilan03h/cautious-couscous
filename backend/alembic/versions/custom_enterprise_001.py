"""Add custom enterprise tables

Revision ID: custom_001
Revises: 
Create Date: 2024-12-11

This migration creates the custom enterprise tables for RBAC and Analytics.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers
revision = 'custom_enterprise_001'
down_revision = '87c52ec39f84'  # Set to latest ESA migration
branch_labels = ('custom',)
depends_on = None


def upgrade() -> None:
    # Create custom user groups table
    op.create_table(
        'custom_user_group',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('document_set_ids', postgresql.ARRAY(sa.Integer()), nullable=False, server_default='{}'),
        sa.Column('assistant_ids', postgresql.ARRAY(sa.Integer()), nullable=False, server_default='{}'),
        sa.Column('connector_ids', postgresql.ARRAY(sa.Integer()), nullable=False, server_default='{}'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.ForeignKeyConstraint(['created_by_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_custom_user_group_name', 'custom_user_group', ['name'], unique=True)
    
    # Create association table for users <-> groups
    op.create_table(
        'custom_user_group_association',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('group_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['group_id'], ['custom_user_group.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('user_id', 'group_id')
    )
    
    # Create audit log table
    op.create_table(
        'custom_user_group_audit_log',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('group_id', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('actor_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('details', sa.String(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['actor_id'], ['user.id'], ),
        sa.ForeignKeyConstraint(['group_id'], ['custom_user_group.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create usage stats table
    op.create_table(
        'custom_usage_stats',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('date', sa.DateTime(), nullable=False),
        sa.Column('total_chats', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('total_messages', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('unique_users', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('total_prompt_tokens', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('total_completion_tokens', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('total_searches', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('avg_search_latency_ms', sa.Float(), nullable=True, server_default='0'),
        sa.Column('total_documents_indexed', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_custom_usage_stats_date', 'custom_usage_stats', ['date'])
    
    # Create user activity table
    op.create_table(
        'custom_user_activity',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('date', sa.DateTime(), nullable=False),
        sa.Column('chat_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('message_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('search_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('document_uploads', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('prompt_tokens', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('completion_tokens', sa.Integer(), nullable=True, server_default='0'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_custom_user_activity_user_id', 'custom_user_activity', ['user_id'])
    op.create_index('ix_custom_user_activity_date', 'custom_user_activity', ['date'])
    
    # Create query log table
    op.create_table(
        'custom_query_log',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('chat_session_id', sa.Integer(), nullable=True),
        sa.Column('query_text', sa.Text(), nullable=False),
        sa.Column('response_text', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.Column('response_time_ms', sa.Integer(), nullable=True),
        sa.Column('prompt_tokens', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('completion_tokens', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('documents_retrieved', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('sources_cited', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('model_name', sa.String(), nullable=True),
        sa.Column('feedback_positive', sa.Boolean(), nullable=True),
        sa.Column('feedback_text', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_custom_query_log_user_id', 'custom_query_log', ['user_id'])
    op.create_index('ix_custom_query_log_timestamp', 'custom_query_log', ['timestamp'])
    op.create_index('ix_custom_query_log_chat_session_id', 'custom_query_log', ['chat_session_id'])
    
    # Create token limit table
    op.create_table(
        'custom_token_limit',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('scope', sa.String(), nullable=False, server_default='global'),
        sa.Column('target_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('target_group_id', sa.Integer(), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('token_budget', sa.Integer(), nullable=False),
        sa.Column('period_hours', sa.Integer(), nullable=False, server_default='24'),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['target_group_id'], ['custom_user_group.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_custom_token_limit_scope', 'custom_token_limit', ['scope'])
    op.create_index('ix_custom_token_limit_target_user_id', 'custom_token_limit', ['target_user_id'])
    op.create_index('ix_custom_token_limit_target_group_id', 'custom_token_limit', ['target_group_id'])
    
    # Create token usage table
    op.create_table(
        'custom_token_usage',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('prompt_tokens', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('completion_tokens', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('period_start', sa.DateTime(), nullable=False),
        sa.Column('period_end', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_custom_token_usage_user_id', 'custom_token_usage', ['user_id'])
    op.create_index('ix_custom_token_usage_period_start', 'custom_token_usage', ['period_start'])


def downgrade() -> None:
    op.drop_table('custom_user_activity')
    op.drop_table('custom_usage_stats')
    op.drop_table('custom_user_group_audit_log')
    op.drop_table('custom_user_group_association')
    op.drop_table('custom_user_group')
