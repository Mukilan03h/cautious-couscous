"""
Tests for myplatform database modules.
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime


class TestConnectorDB:
    """Tests for connector database operations."""
    
    def test_fetch_sources_with_connectors(self):
        """Should return list of document sources with connectors."""
        from myplatform.db.connector import fetch_sources_with_connectors
        
        mock_session = MagicMock()
        mock_session.query.return_value.all.return_value = [
            ("GOOGLE_DRIVE",),
            ("SLACK",),
        ]
        
        result = fetch_sources_with_connectors(mock_session)
        assert isinstance(result, list)


class TestDocumentDB:
    """Tests for document database operations."""
    
    def test_upsert_document_external_perms_new_doc(self):
        """Should create new document with permissions."""
        from myplatform.db.document import upsert_document_external_perms
        from esa.access.models import ExternalAccess
        from esa.configs.constants import DocumentSource
        
        mock_session = MagicMock()
        mock_session.scalars.return_value.first.return_value = None
        
        access = ExternalAccess(
            external_user_emails={"user@test.com"},
            external_user_group_ids={"group1"},
            is_public=False,
        )
        
        result = upsert_document_external_perms(
            db_session=mock_session,
            doc_id="doc123",
            external_access=access,
            source_type=DocumentSource.GOOGLE_DRIVE,
        )
        
        assert result is True  # New document created
        mock_session.add.assert_called_once()


class TestDocumentSetDB:
    """Tests for document set database operations."""
    
    def test_make_doc_set_private_clears_existing(self):
        """Should clear existing user/group associations."""
        from myplatform.db.document_set import make_doc_set_private
        
        mock_session = MagicMock()
        
        make_doc_set_private(
            document_set_id=1,
            user_ids=None,
            group_ids=None,
            db_session=mock_session,
        )
        
        # Should call delete on both user and group associations
        assert mock_session.query.call_count >= 2


class TestPersonaDB:
    """Tests for persona database operations."""
    
    def test_make_persona_private(self):
        """Should create user and group associations."""
        from myplatform.db.persona import make_persona_private
        from uuid import UUID
        
        mock_session = MagicMock()
        
        with patch('myplatform.db.persona.create_notification'):
            make_persona_private(
                persona_id=1,
                creator_user_id=UUID('12345678-1234-1234-1234-123456789012'),
                user_ids=[UUID('12345678-1234-1234-1234-123456789012')],
                group_ids=[1, 2],
                db_session=mock_session,
            )
        
        mock_session.commit.assert_called_once()


class TestSamlDB:
    """Tests for SAML database operations."""
    
    def test_upsert_saml_account_new(self):
        """Should create new SAML account."""
        from myplatform.db.saml import upsert_saml_account
        from uuid import UUID
        
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.one_or_none.return_value = None
        
        with patch('myplatform.db.saml.func') as mock_func:
            mock_func.now.return_value = datetime.now()
            result = upsert_saml_account(
                user_id=UUID('12345678-1234-1234-1234-123456789012'),
                cookie="test_cookie",
                db_session=mock_session,
            )
        
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()


class TestConnectorCredentialPairDB:
    """Tests for connector credential pair database operations."""
    
    def test_get_all_auto_sync_cc_pairs(self):
        """Should return all auto-sync cc_pairs."""
        from myplatform.db.connector_credential_pair import get_all_auto_sync_cc_pairs
        
        mock_session = MagicMock()
        mock_session.query.return_value.where.return_value.all.return_value = [
            MagicMock(id=1),
            MagicMock(id=2),
        ]
        
        result = get_all_auto_sync_cc_pairs(mock_session)
        assert len(result) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
