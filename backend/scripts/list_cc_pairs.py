"""Script to list all connector-credential pairs and their status."""
import os
import sys

# Add parent directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from dotenv import load_dotenv
load_dotenv()

from esa.db.engine.sql_engine import SqlEngine, get_session_with_current_tenant
from esa.db.models import ConnectorCredentialPair
from shared_configs.configs import POSTGRES_DEFAULT_SCHEMA
from shared_configs.contextvars import CURRENT_TENANT_ID_CONTEXTVAR

# Initialize engine
SqlEngine.init_engine(pool_size=5, max_overflow=5)
CURRENT_TENANT_ID_CONTEXTVAR.set(POSTGRES_DEFAULT_SCHEMA)

with get_session_with_current_tenant() as db_session:
    pairs = db_session.query(ConnectorCredentialPair).all()
    print("\n=== Connector Credential Pairs ===")
    for p in pairs:
        print(f"CC_PAIR_ID: {p.id} | Connector: {p.connector.name} | Status: {p.status}")
    print("===================================\n")
