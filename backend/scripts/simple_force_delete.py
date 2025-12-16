"""Simple script to force delete a stuck connector by cc_pair_id."""
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import text
from esa.db.engine.sql_engine import SqlEngine, get_session_with_current_tenant
from esa.db.models import ConnectorCredentialPair
from shared_configs.configs import POSTGRES_DEFAULT_SCHEMA
from shared_configs.contextvars import CURRENT_TENANT_ID_CONTEXTVAR

CC_PAIR_ID = 36  # Change this to your connector ID

# Initialize engine
SqlEngine.init_engine(pool_size=5, max_overflow=5)
CURRENT_TENANT_ID_CONTEXTVAR.set(POSTGRES_DEFAULT_SCHEMA)

print(f"\n=== Force Deleting CC Pair ID: {CC_PAIR_ID} ===")

with get_session_with_current_tenant() as db_session:
    # Get the cc pair
    cc_pair = db_session.query(ConnectorCredentialPair).filter(
        ConnectorCredentialPair.id == CC_PAIR_ID
    ).first()
    
    if not cc_pair:
        print(f"CC Pair {CC_PAIR_ID} not found!")
        sys.exit(1)
    
    connector_id = cc_pair.connector_id
    credential_id = cc_pair.credential_id
    
    print(f"Found: Connector ID={connector_id}, Credential ID={credential_id}")
    print(f"Status: {cc_pair.status}")
    
    # Delete related records in order
    print("Deleting index_attempt records...")
    db_session.execute(text(f"DELETE FROM index_attempt WHERE connector_credential_pair_id = {CC_PAIR_ID}"))
    
    print("Deleting document_set__connector_credential_pair records...")
    db_session.execute(text(f"DELETE FROM document_set__connector_credential_pair WHERE connector_credential_pair_id = {CC_PAIR_ID}"))
    
    print("Deleting user_group__connector_credential_pair records...")
    db_session.execute(text(f"DELETE FROM user_group__connector_credential_pair WHERE cc_pair_id = {CC_PAIR_ID}"))
    
    print("Deleting connector_credential_pair record...")
    db_session.execute(text(f"DELETE FROM connector_credential_pair WHERE id = {CC_PAIR_ID}"))
    
    print("Deleting connector record...")
    db_session.execute(text(f"DELETE FROM connector WHERE id = {connector_id}"))
    
    db_session.commit()
    print("\n=== Successfully deleted! ===\n")
