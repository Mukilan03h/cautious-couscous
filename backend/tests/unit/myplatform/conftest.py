"""
Shared fixtures for myplatform unit tests
"""
import pytest
from collections.abc import Generator
from datetime import datetime
from typing import Any
from unittest.mock import MagicMock, patch
from uuid import uuid4, UUID

import os

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

# Import our custom models - ALL must be imported so Base.metadata contains them
from myplatform.db.user_groups import CustomUserGroup, CustomUserGroupAuditLog, user_group_association
from myplatform.db.token_limits import CustomTokenLimit, CustomTokenUsage
from myplatform.db.analytics import CustomUsageStats, CustomUserActivity
from myplatform.db.standard_answers import CustomStandardAnswer, CustomStandardAnswerCategory, standard_answer_category_association
from myplatform.db.query_history import CustomQueryLog
from myplatform.db.feature_flags import CustomFeatureFlag
from myplatform.db.tenants import CustomTenant, CustomTenantUser
from myplatform.db.permissions import CustomDocumentACL
from myplatform.db.evals import CustomEvalDataset, CustomEvalQuestion, CustomEvalRun, CustomEvalResult
from myplatform.db.connector_permissions import CustomConnectorPermissionSync

# Import the Base from esa to get all table definitions
from esa.db.models import Base


def get_test_database_url() -> str:
    """Get database URL for testing. Prefers PostgreSQL from environment."""
    # Try environment variables in order of preference
    for env_var in ["TEST_DATABASE_URL", "POSTGRES_URL", "POSTGRES_HOST"]:
        if url := os.environ.get(env_var):
            if env_var == "POSTGRES_HOST":
                # Build URL from components
                user = os.environ.get("POSTGRES_USER", "postgres")
                password = os.environ.get("POSTGRES_PASSWORD", "password")
                db = os.environ.get("POSTGRES_DB", "postgres")
                return f"postgresql://{user}:{password}@{url}/{db}"
            return url
    
    # No PostgreSQL available
    return None


# Skip all tests in this module if PostgreSQL is not configured
# ESA models use PostgreSQL-specific types (ARRAY, JSONB) that SQLite cannot compile
_db_url = get_test_database_url()
pytestmark = pytest.mark.skipif(
    _db_url is None,
    reason="MyPlatform tests require PostgreSQL. Set TEST_DATABASE_URL, POSTGRES_URL, or POSTGRES_HOST."
)


@pytest.fixture(scope="function")
def db_engine():
    """Create a database engine for testing. Requires PostgreSQL."""
    database_url = _db_url
    
    if database_url is None:
        pytest.skip("PostgreSQL not configured")
    
    engine = create_engine(database_url)
    
    # Drop all tables first to ensure clean slate
    with engine.begin() as conn:
        # Drop all tables in cascade mode
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    
    # Create all tables
    Base.metadata.create_all(engine)
    
    yield engine
    
    # Cleanup: drop tables after tests  
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    
    engine.dispose()


@pytest.fixture
def db_session(db_engine) -> Generator[Session, None, None]:
    """Create a database session for testing"""
    SessionLocal = sessionmaker(bind=db_engine, autocommit=False, autoflush=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def sample_user_id() -> UUID:
    """Sample user UUID for testing"""
    return uuid4()


@pytest.fixture
def sample_user_id_2() -> UUID:
    """Second sample user UUID for testing"""
    return uuid4()


@pytest.fixture
def sample_group_ids() -> list[int]:
    """Sample group IDs for testing"""
    return [1, 2, 3]


@pytest.fixture
def mock_db_session() -> MagicMock:
    """Create a mock database session for unit tests that don't need real db"""
    mock_session = MagicMock(spec=Session)
    mock_session.add = MagicMock()
    mock_session.commit = MagicMock()
    mock_session.refresh = MagicMock()
    mock_session.rollback = MagicMock()
    mock_session.delete = MagicMock()
    mock_session.get = MagicMock(return_value=None)
    mock_session.scalar = MagicMock(return_value=None)
    mock_session.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
    return mock_session
