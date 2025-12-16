
import os
import sys
import logging
from datetime import datetime, timedelta

# Add backend to path - ensure we point to f:\Onyx\backend
# If script is in f:\Onyx\backend\tests\servicenow\verify..., 
# os.path.dirname(script) is f:\Onyx\backend\tests\servicenow
# We want f:\Onyx\backend
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
# The above assumes script is in tests/servicenow/. 
# Actually let's just be explicit or use relative from CWD if we run from root.
# If running from f:\Onyx\backend
sys.path.append(os.getcwd())

# Mock missing dependencies
import types
from unittest.mock import MagicMock
if 'retry' not in sys.modules:
    m = types.ModuleType('retry')
    m.retry = lambda *args, **kwargs: lambda f: f
    sys.modules['retry'] = m
    
from esa.connectors.servicenow.connector import ServiceNowConnector
from esa.connectors.models import Document, ConnectorFailure

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_orchestration():
    print("--- Starting ServiceNow Connector Orchestration Verification ---")

    # 1. Instantiate Connector
    connector = ServiceNowConnector(content_type="incidents") # Start with simple Incidents
    
    # 2. Load Credentials
    creds = {
        "servicenow_instance_url": "https://dev314000.service-now.com",
        "servicenow_username": "admin",
        "servicenow_password": "Y=/n32jtZnUA"
    }
    
    try:
        connector.load_credentials(creds)
        print("✅ Credentials loaded.")
    except Exception as e:
        print(f"❌ Failed to load credentials: {e}")
        return

    # 3. Validate Settings
    try:
        connector.validate_connector_settings()
        print("✅ Connection validated (validate_connector_settings).")
    except Exception as e:
        print(f"❌ Connection validation failed: {e}")
        return

    # 4. Fetch Documents (Simulate Ingestion)
    print("--- Fetching Documents (Incidents) ---")
    
    dummy_checkpoint = connector.build_dummy_checkpoint()
    
    doc_count = 0
    
    # Fetch for last 365 days to ensure we get some data
    start_time = (datetime.now() - timedelta(days=365)).timestamp()
    end_time = datetime.now().timestamp()
    
    try:
        # Use load_from_checkpoint
        for item in connector.load_from_checkpoint(start_time, end_time, dummy_checkpoint):
            if isinstance(item, Document):
                doc_count += 1
                print(f"📄 Found Document: {item.id}")
                print(f"   - Title: {item.semantic_identifier}")
                print(f"   - Link: {item.sections[0].link}")
                print(f"   - Metadata: {item.metadata}")
                
                # Check for Resolved References (Dot-Walking) check
                # Our basic connector implementation currently just does raw fetch
                # But EnhancedClient inside *could* be used for more if we updated _record_to_document
                # For now, we verify basic pipeline works (which uses EnhancedClient.get_records compatible mode)
                
                if doc_count >= 3:
                    print("... stopping after 3 docs ...")
                    break
                    
            elif isinstance(item, ConnectorFailure):
                print(f"⚠️ Failure: {item.failure_message}")
    except Exception as e:
        print(f"❌ Error during ingestion: {e}")
        import traceback
        traceback.print_exc()

    if doc_count > 0:
        print(f"✅ Successfully fetched {doc_count} documents.")
        print("🎉 Connector Orchestration Verified!")
    else:
        print("⚠️ No documents found. (Might be empty instance or date range issue)")

if __name__ == "__main__":
    verify_orchestration()
