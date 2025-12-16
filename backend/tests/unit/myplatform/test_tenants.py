"""
Unit tests for myplatform.db.tenants
"""
import pytest
from uuid import uuid4

from myplatform.db.tenants import (
    CustomTenant,
    CustomTenantUser,
    create_tenant,
    get_tenant_by_slug,
    get_tenant_by_id,
    get_all_tenants,
    update_tenant,
    add_user_to_tenant,
    remove_user_from_tenant,
    get_user_tenants,
    get_tenant_users,
    check_user_in_tenant,
    get_user_tenant_role,
)


class TestTenantCRUD:
    """Tests for tenant CRUD operations"""
    
    def test_create_tenant(self, db_session):
        """Test creating a tenant"""
        tenant = create_tenant(
            db_session,
            name='Acme Corporation',
            slug='acme',
            display_name='Acme Corp',
            max_users=100,
            max_documents=10000,
        )
        
        assert tenant.id is not None
        assert tenant.name == 'Acme Corporation'
        assert tenant.slug == 'acme'
        assert tenant.display_name == 'Acme Corp'
        assert tenant.max_users == 100
        assert tenant.is_active is True
    
    def test_create_tenant_with_settings(self, db_session):
        """Test creating a tenant with custom settings"""
        tenant = create_tenant(
            db_session,
            name='Tech Corp',
            slug='techcorp',
            settings={'theme': 'dark', 'language': 'en'},
        )
        
        assert tenant.settings == {'theme': 'dark', 'language': 'en'}
    
    def test_get_tenant_by_slug(self, db_session):
        """Test retrieving tenant by slug"""
        create_tenant(db_session, name='Test Org', slug='testorg')
        
        tenant = get_tenant_by_slug(db_session, 'testorg')
        
        assert tenant is not None
        assert tenant.slug == 'testorg'
    
    def test_get_tenant_by_id(self, db_session):
        """Test retrieving tenant by ID"""
        created = create_tenant(db_session, name='ID Test', slug='idtest')
        
        tenant = get_tenant_by_id(db_session, created.id)
        
        assert tenant is not None
        assert tenant.id == created.id
    
    def test_get_all_tenants(self, db_session):
        """Test getting all active tenants"""
        create_tenant(db_session, name='Tenant A', slug='tenant-a')
        create_tenant(db_session, name='Tenant B', slug='tenant-b')
        
        tenants = get_all_tenants(db_session)
        slugs = [t.slug for t in tenants]
        
        assert 'tenant-a' in slugs
        assert 'tenant-b' in slugs
    
    def test_update_tenant(self, db_session):
        """Test updating a tenant"""
        tenant = create_tenant(db_session, name='Old Name', slug='update-test')
        
        updated = update_tenant(
            db_session,
            tenant_id=tenant.id,
            name='New Name',
            display_name='Updated Display',
            max_users=500,
        )
        
        assert updated.name == 'New Name'
        assert updated.display_name == 'Updated Display'
        assert updated.max_users == 500
    
    def test_update_tenant_deactivate(self, db_session):
        """Test deactivating a tenant"""
        tenant = create_tenant(db_session, name='Active Tenant', slug='active')
        
        updated = update_tenant(db_session, tenant.id, is_active=False)
        
        assert updated.is_active is False


class TestTenantUserManagement:
    """Tests for tenant user membership"""
    
    def test_add_user_to_tenant(self, db_session, sample_user_id):
        """Test adding a user to a tenant"""
        tenant = create_tenant(db_session, name='Test Tenant', slug='test-tenant')
        
        membership = add_user_to_tenant(
            db_session,
            tenant_id=tenant.id,
            user_id=sample_user_id,
            role='admin',
        )
        
        assert membership.tenant_id == tenant.id
        assert membership.user_id == sample_user_id
        assert membership.role == 'admin'
        assert membership.is_active is True
    
    def test_add_user_to_tenant_update_role(self, db_session, sample_user_id):
        """Test updating user role in tenant"""
        tenant = create_tenant(db_session, name='Role Test', slug='role-test')
        
        add_user_to_tenant(db_session, tenant.id, sample_user_id, role='member')
        membership = add_user_to_tenant(db_session, tenant.id, sample_user_id, role='admin')
        
        assert membership.role == 'admin'
    
    def test_remove_user_from_tenant(self, db_session, sample_user_id):
        """Test removing a user from a tenant"""
        tenant = create_tenant(db_session, name='Remove Test', slug='remove-test')
        add_user_to_tenant(db_session, tenant.id, sample_user_id)
        
        result = remove_user_from_tenant(db_session, tenant.id, sample_user_id)
        
        assert result is True
    
    def test_get_user_tenants(self, db_session, sample_user_id):
        """Test getting all tenants for a user"""
        tenant1 = create_tenant(db_session, name='Tenant 1', slug='tenant-1')
        tenant2 = create_tenant(db_session, name='Tenant 2', slug='tenant-2')
        
        add_user_to_tenant(db_session, tenant1.id, sample_user_id)
        add_user_to_tenant(db_session, tenant2.id, sample_user_id)
        
        tenant_ids = get_user_tenants(db_session, sample_user_id)
        
        assert tenant1.id in tenant_ids
        assert tenant2.id in tenant_ids
    
    def test_get_tenant_users(self, db_session, sample_user_id, sample_user_id_2):
        """Test getting all users in a tenant"""
        tenant = create_tenant(db_session, name='Users Test', slug='users-test')
        
        add_user_to_tenant(db_session, tenant.id, sample_user_id)
        add_user_to_tenant(db_session, tenant.id, sample_user_id_2)
        
        users = get_tenant_users(db_session, tenant.id)
        user_ids = [u.user_id for u in users]
        
        assert sample_user_id in user_ids
        assert sample_user_id_2 in user_ids
    
    def test_check_user_in_tenant(self, db_session, sample_user_id, sample_user_id_2):
        """Test checking if user is in a tenant"""
        tenant = create_tenant(db_session, name='Check Test', slug='check-test')
        add_user_to_tenant(db_session, tenant.id, sample_user_id)
        
        assert check_user_in_tenant(db_session, sample_user_id, tenant.id) is True
        assert check_user_in_tenant(db_session, sample_user_id_2, tenant.id) is False
    
    def test_get_user_tenant_role(self, db_session, sample_user_id):
        """Test getting user's role in a tenant"""
        tenant = create_tenant(db_session, name='Role Check', slug='role-check')
        add_user_to_tenant(db_session, tenant.id, sample_user_id, role='admin')
        
        role = get_user_tenant_role(db_session, sample_user_id, tenant.id)
        
        assert role == 'admin'
    
    def test_get_user_tenant_role_not_member(self, db_session, sample_user_id):
        """Test getting role when user is not a member"""
        tenant = create_tenant(db_session, name='Not Member', slug='not-member')
        
        role = get_user_tenant_role(db_session, sample_user_id, tenant.id)
        
        assert role is None
