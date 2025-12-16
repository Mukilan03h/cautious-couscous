"""Verify Live ServiceNow Connection and Enhanced Client Features.

USAGE:
    python tests/servicenow/verify_live_connection.py

Requires internet access to dev314000.service-now.com.
"""

import sys
import logging
from typing import Any

# Add backend to path to allow imports
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

try:
    from esa.connectors.servicenow.enhanced_client import EnhancedServiceNowClient
except ImportError:
    # Handle case where esa package is not in python path
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
    from esa.connectors.servicenow.enhanced_client import EnhancedServiceNowClient

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Credentials provided by user
INSTANCE_URL = "https://dev314000.service-now.com"
USERNAME = "admin"
PASSWORD = "Y=/n32jtZnUA"

def verify_enhanced_client():
    logger.info(f"Connecting to {INSTANCE_URL}...")
    
    try:
        client = EnhancedServiceNowClient(
            instance_url=INSTANCE_URL,
            username=USERNAME,
            password=PASSWORD
        )
        
        # 1. Validate Connection
        if client.validate_connection():
            logger.info("✅ Connection Validated!")
        else:
            logger.error("❌ Connection Validation Failed!")
            return

        # 2. Test Get Records (Incident)
        logger.info("\n--- Testing Table API (Incident) ---")
        incidents = client.get_records_enhanced(
            table="incident",
            limit=1,
            fields=["number", "short_description", "sys_id"]
        )
        results = incidents.get("result", [])
        if results:
            inc = results[0]
            inc_number = inc.get('number')
            if isinstance(inc_number, dict):
                inc_number = inc_number.get('value')
            
            logger.info(f"✅ Found Incident: {inc_number} - {inc.get('short_description')}")
            
            # 3. Test Polymorphic Task Lookup
            logger.info(f"\n--- Testing Polymorphic Task Lookup ({inc_number}) ---")
            task = client.get_task_by_number(inc_number)
            if task and task.get('_table') == 'incident':
                logger.info(f"✅ Polymorphic Lookup Successful! Identified table: {task['_table']}")
            else:
                logger.error(f"❌ Polymorphic Lookup Failed: {task}")
        else:
            logger.warning("⚠️ No incidents found to test.")

        # 4. Test Dot-Walking
        logger.info("\n--- Testing Dot-Walking ---")
        dot_walk_results = client.get_records_enhanced(
            table="incident",
            limit=1,
            fields=["assigned_to.name", "assigned_to.email"]
        )
        if dot_walk_results.get("result"):
            rec = dot_walk_results["result"][0]
            logger.info(f"✅ Dot-Walking Result: {rec}")
        else:
            logger.warning("⚠️ No records found for dot-walking test.")

        # 5. Test Service Catalog (List Items)
        logger.info("\n--- Testing Service Catalog (Get Items) ---")
        # Reuse client's request method or access endpoint manually as EnhancedClient 
        # doesn't have specific catalog methods mixed in (it's separate client)
        # But we can check basic connectivity to SC endpoints
        sc_items = client.get("api/sn_sc/servicecatalog/items", params={"sysparm_limit": 1})
        if sc_items.get("result"):
            item = sc_items["result"][0]
            logger.info(f"✅ Found Catalog Item: {item.get('name')}")
        else:
            logger.warning("⚠️ No catalog items found.")

        logger.info("\n🎉 Verification Complete!")

    except Exception as e:
        logger.error(f"❌ Verification Failed with Exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify_enhanced_client()
