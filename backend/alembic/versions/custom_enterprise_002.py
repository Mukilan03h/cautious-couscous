"""
Custom Enterprise Platform - Complete Database Migration
Creates all tables for P1-P5 features.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'custom_enterprise_002'
down_revision = 'custom_enterprise_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ========== P1: Standard Answers ==========
    op.create_table(
        'custom_standard_answer_category',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False, unique=True),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table(
        'custom_standard_answer',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('keyword', sa.String(), nullable=False),
        sa.Column('answer', sa.Text(), nullable=False),
        sa.Column('match_regex', sa.Boolean(), server_default='false'),
        sa.Column('match_any_keywords', sa.Boolean(), server_default='true'),
        sa.Column('active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table(
        'custom_standard_answer_category_assoc',
        sa.Column('answer_id', sa.Integer(), sa.ForeignKey('custom_standard_answer.id'), nullable=False),
        sa.Column('category_id', sa.Integer(), sa.ForeignKey('custom_standard_answer_category.id'), nullable=False),
        sa.PrimaryKeyConstraint('answer_id', 'category_id')
    )
    
    # ========== P2: Document ACLs ==========
    op.create_table(
        'custom_document_acl',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('resource_type', sa.String(), nullable=False),
        sa.Column('resource_id', sa.Integer(), nullable=False),
        sa.Column('user_ids', postgresql.ARRAY(postgresql.UUID(as_uuid=True)), server_default='{}'),
        sa.Column('group_ids', postgresql.ARRAY(sa.Integer()), server_default='{}'),
        sa.Column('is_public', sa.Boolean(), server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_custom_document_acl_resource', 'custom_document_acl', ['resource_type', 'resource_id'])
    
    # ========== P3: Connector Permission Sync ==========
    op.create_table(
        'custom_connector_permission_sync',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('connector_id', sa.Integer(), nullable=False),
        sa.Column('connector_type', sa.String(), nullable=False),
        sa.Column('last_sync_at', sa.DateTime(), nullable=True),
        sa.Column('sync_enabled', sa.Boolean(), server_default='true'),
        sa.Column('sync_status', sa.String(), server_default="'pending'"),
        sa.Column('last_error', sa.String(), nullable=True),
        sa.Column('sync_config', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_custom_connector_permission_sync_connector_id', 'custom_connector_permission_sync', ['connector_id'])
    
    op.create_table(
        'custom_external_user_mapping',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('connector_type', sa.String(), nullable=False),
        sa.Column('external_user_id', sa.String(), nullable=False),
        sa.Column('external_email', sa.String(), nullable=True),
        sa.Column('external_name', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('last_verified_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_custom_external_user_mapping_user_id', 'custom_external_user_mapping', ['user_id'])
    op.create_index('ix_custom_external_user_mapping_external', 'custom_external_user_mapping', ['connector_type', 'external_user_id'])
    
    op.create_table(
        'custom_external_resource_permission',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('connector_id', sa.Integer(), nullable=False),
        sa.Column('connector_type', sa.String(), nullable=False),
        sa.Column('resource_id', sa.String(), nullable=False),
        sa.Column('resource_type', sa.String(), nullable=False),
        sa.Column('resource_name', sa.String(), nullable=True),
        sa.Column('allowed_external_user_ids', postgresql.JSONB(), server_default='[]'),
        sa.Column('allowed_external_group_ids', postgresql.JSONB(), server_default='[]'),
        sa.Column('is_public', sa.Boolean(), server_default='false'),
        sa.Column('synced_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_custom_external_resource_permission_connector', 'custom_external_resource_permission', ['connector_id', 'resource_id'])
    
    # ========== P4: Multi-Tenancy ==========
    op.create_table(
        'custom_tenant',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False, unique=True),
        sa.Column('slug', sa.String(), nullable=False, unique=True),
        sa.Column('display_name', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('max_users', sa.Integer(), nullable=True),
        sa.Column('max_documents', sa.Integer(), nullable=True),
        sa.Column('max_storage_gb', sa.Integer(), nullable=True),
        sa.Column('settings', postgresql.JSONB(), server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_custom_tenant_slug', 'custom_tenant', ['slug'])
    
    op.create_table(
        'custom_tenant_user',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('custom_tenant.id'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.String(), server_default="'member'"),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_custom_tenant_user_tenant_id', 'custom_tenant_user', ['tenant_id'])
    op.create_index('ix_custom_tenant_user_user_id', 'custom_tenant_user', ['user_id'])
    
    # ========== P5: Feature Flags ==========
    op.create_table(
        'custom_feature_flag',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False, unique=True),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('enabled_by_default', sa.Boolean(), server_default='false'),
        sa.Column('enabled_for_all', sa.Boolean(), server_default='false'),
        sa.Column('enabled_tenant_ids', postgresql.ARRAY(sa.Integer()), server_default='{}'),
        sa.Column('enabled_user_ids', postgresql.ARRAY(postgresql.UUID(as_uuid=True)), server_default='{}'),
        sa.Column('enabled_group_ids', postgresql.ARRAY(sa.Integer()), server_default='{}'),
        sa.Column('disabled_tenant_ids', postgresql.ARRAY(sa.Integer()), server_default='{}'),
        sa.Column('disabled_user_ids', postgresql.ARRAY(postgresql.UUID(as_uuid=True)), server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_custom_feature_flag_name', 'custom_feature_flag', ['name'])
    
    # ========== P5: Evals ==========
    op.create_table(
        'custom_eval_dataset',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table(
        'custom_eval_question',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('dataset_id', sa.Integer(), sa.ForeignKey('custom_eval_dataset.id'), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('expected_answer', sa.Text(), nullable=True),
        sa.Column('expected_sources', postgresql.JSONB(), server_default='[]'),
        sa.Column('category', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_custom_eval_question_dataset_id', 'custom_eval_question', ['dataset_id'])
    
    op.create_table(
        'custom_eval_run',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('dataset_id', sa.Integer(), sa.ForeignKey('custom_eval_dataset.id'), nullable=False),
        sa.Column('status', sa.String(), server_default="'pending'"),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('persona_id', sa.Integer(), nullable=True),
        sa.Column('model_name', sa.String(), nullable=True),
        sa.Column('avg_relevance_score', sa.Float(), nullable=True),
        sa.Column('avg_accuracy_score', sa.Float(), nullable=True),
        sa.Column('total_questions', sa.Integer(), server_default='0'),
        sa.Column('passed_questions', sa.Integer(), server_default='0'),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table(
        'custom_eval_result',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('run_id', sa.Integer(), sa.ForeignKey('custom_eval_run.id'), nullable=False),
        sa.Column('question_id', sa.Integer(), sa.ForeignKey('custom_eval_question.id'), nullable=False),
        sa.Column('generated_answer', sa.Text(), nullable=True),
        sa.Column('sources_used', postgresql.JSONB(), server_default='[]'),
        sa.Column('relevance_score', sa.Float(), nullable=True),
        sa.Column('accuracy_score', sa.Float(), nullable=True),
        sa.Column('source_match_score', sa.Float(), nullable=True),
        sa.Column('passed', sa.Boolean(), nullable=True),
        sa.Column('response_time_ms', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_custom_eval_result_run_id', 'custom_eval_result', ['run_id'])


def downgrade() -> None:
    op.drop_table('custom_eval_result')
    op.drop_table('custom_eval_run')
    op.drop_table('custom_eval_question')
    op.drop_table('custom_eval_dataset')
    op.drop_table('custom_feature_flag')
    op.drop_table('custom_tenant_user')
    op.drop_table('custom_tenant')
    op.drop_table('custom_external_resource_permission')
    op.drop_table('custom_external_user_mapping')
    op.drop_table('custom_connector_permission_sync')
    op.drop_table('custom_document_acl')
    op.drop_table('custom_standard_answer_category_assoc')
    op.drop_table('custom_standard_answer')
    op.drop_table('custom_standard_answer_category')
