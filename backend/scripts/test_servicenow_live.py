"""Test ServiceNow connector with real credentials."""
import os
import sys
import time

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from dotenv import load_dotenv
load_dotenv()

# Test credentials
SERVICENOW_INSTANCE_URL = "https://dev314000.service-now.com/"
SERVICENOW_USERNAME = "admin"
SERVICENOW_PASSWORD = "Y=/n32jtZnUA"

print("=" * 60)
print("ServiceNow Connector Test")
print("=" * 60)
print(f"Instance: {SERVICENOW_INSTANCE_URL}")
print(f"Username: {SERVICENOW_USERNAME}")
print()

# Test 1: Direct API connection using EnhancedServiceNowClient
print("Test 1: Testing EnhancedServiceNowClient...")
try:
    from esa.connectors.servicenow.enhanced_client import EnhancedServiceNowClient
    
    client = EnhancedServiceNowClient(
        instance_url=SERVICENOW_INSTANCE_URL,
        username=SERVICENOW_USERNAME,
        password=SERVICENOW_PASSWORD,
    )
    
    # Test with incident table
    print("  Fetching incidents from 'incident' table...")
    incidents = client.get_records_enhanced(table="incident", limit=5)
    print(f"  ✅ Found {len(incidents)} incidents")
    
    if incidents:
        inc = incidents[0]
        print(f"  Sample: {inc.get('number', 'N/A')} - {str(inc.get('short_description', 'N/A'))[:50]}")
    
except Exception as e:
    import traceback
    print(f"  ❌ Error: {e}")
    traceback.print_exc()

# Test 2: Knowledge Articles
print("\nTest 2: Testing Knowledge Articles...")
try:
    kb_articles = client.get_records_enhanced(table="kb_knowledge", limit=5)
    print(f"  ✅ Found {len(kb_articles)} knowledge articles")
    
    if kb_articles:
        kb = kb_articles[0]
        print(f"  Sample KB: {kb.get('number', 'N/A')} - {str(kb.get('short_description', 'N/A'))[:50]}")
        
except Exception as e:
    print(f"  ❌ Error fetching KB articles: {e}")

# Test 3: Full Connector with load_from_checkpoint
print("\nTest 3: Testing full connector pipeline...")
try:
    from esa.connectors.servicenow.connector import ServiceNowConnector, ServiceNowConnectorCheckpoint
    
    connector = ServiceNowConnector(content_type="incidents")
    connector.load_credentials({
        "servicenow_instance_url": SERVICENOW_INSTANCE_URL,
        "servicenow_username": SERVICENOW_USERNAME,
        "servicenow_password": SERVICENOW_PASSWORD,
    })
    
    # Create checkpoint
    checkpoint = ServiceNowConnectorCheckpoint(table_offsets={}, current_table_index=0)
    start_time = 0  # Unix epoch
    end_time = int(time.time())  # Now
    
    print("  Fetching documents via connector.load_from_checkpoint()...")
    doc_count = 0
    for doc_batch in connector.load_from_checkpoint(start_time, end_time, checkpoint):
        for doc in doc_batch:
            doc_count += 1
            if doc_count <= 3:
                print(f"    Doc {doc_count}: {doc.semantic_identifier[:60]}...")
            if doc_count >= 10:
                break
        if doc_count >= 10:
            break
    
    print(f"  ✅ Successfully fetched {doc_count} documents")
    
except Exception as e:
    import traceback
    print(f"  ❌ Error: {e}")
    traceback.print_exc()

print("\n" + "=" * 60)
print("Test Complete!")
print("=" * 60)
