"""Test ServiceNow Service Catalog fetching.

Tests the connector's ability to fetch Service Catalog items.
"""
import os
import sys

# Add backend to path
sys.path.append(os.getcwd())

from esa.connectors.servicenow.connector import ServiceNowConnector, CONTENT_TYPE_TABLES
from esa.connectors.models import Document
from esa.connectors.interfaces import ConnectorFailure
from datetime import datetime, timedelta

def test_service_catalog():
    print("=" * 60)
    print("ServiceNow Service Catalog Test")
    print("=" * 60)
    
    # Credentials
    creds = {
        "servicenow_instance_url": "https://dev314000.service-now.com",
        "servicenow_username": "admin",
        "servicenow_password": "Y=/n32jtZnUA"
    }
    
    # Show available content types for catalog
    print("\n📋 Available Catalog Content Types:")
    for ct, tables in CONTENT_TYPE_TABLES.items():
        if "catalog" in ct.lower():
            print(f"  - {ct}: {tables}")
    
    # Test catalog_items
    print("\n" + "=" * 60)
    print("Testing: catalog_items (sc_cat_item table)")
    print("=" * 60)
    
    connector = ServiceNowConnector(content_type="catalog_items")
    
    try:
        connector.load_credentials(creds)
        print("✅ Credentials loaded")
    except Exception as e:
        print(f"❌ Credential load failed: {e}")
        return
    
    try:
        connector.validate_connector_settings()
        print("✅ Connection validated")
    except Exception as e:
        print(f"❌ Connection validation failed: {e}")
        return
    
    # Fetch catalog items
    print("\n--- Fetching Service Catalog Items ---")
    
    checkpoint = connector.build_dummy_checkpoint()
    start_time = (datetime.now() - timedelta(days=365)).timestamp()
    end_time = datetime.now().timestamp()
    
    doc_count = 0
    try:
        for item in connector.load_from_checkpoint(start_time, end_time, checkpoint):
            if isinstance(item, Document):
                doc_count += 1
                print(f"\n📦 Catalog Item #{doc_count}:")
                print(f"   ID: {item.id}")
                print(f"   Title: {item.semantic_identifier}")
                if item.sections:
                    print(f"   Link: {item.sections[0].link}")
                    # Show first 200 chars of content
                    text = item.sections[0].text[:200] + "..." if len(item.sections[0].text) > 200 else item.sections[0].text
                    print(f"   Content: {text}")
                print(f"   Metadata: {item.metadata}")
                
                if doc_count >= 5:
                    print("\n... (stopping after 5 items)")
                    break
                    
            elif isinstance(item, ConnectorFailure):
                print(f"⚠️ Failure: {item.failure_message}")
                
    except Exception as e:
        print(f"❌ Error during fetch: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("\n" + "=" * 60)
    if doc_count > 0:
        print(f"✅ SUCCESS: Fetched {doc_count} Service Catalog items!")
    else:
        print("⚠️ No Service Catalog items found (instance may be empty)")
    print("=" * 60)

if __name__ == "__main__":
    test_service_catalog()
