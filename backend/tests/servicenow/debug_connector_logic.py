
import os
import sys
import logging
import time

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from esa.connectors.servicenow.connector import ServiceNowConnector, ServiceNowConnectorCheckpoint
from esa.connectors.models import Document, ConnectorFailure

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def debug_connector():
    logger.info("Initializing ServiceNowConnector...")
    # Simulate UI selection: "incidents"
    connector = ServiceNowConnector(content_type="incidents")
    
    config = {
        "servicenow_instance_url": "https://dev314000.service-now.com",
        "servicenow_username": "admin",
        "servicenow_password": "Y=/n32jtZnUA"
    }
    
    logger.info("Loading credentials...")
    connector.load_credentials(config)
    
    logger.info("Validating settings...")
    try:
        connector.validate_connector_settings()
        logger.info("✅ Validation successful")
    except Exception as e:
        logger.error(f"❌ Validation failed: {e}")
        return

    # Simulate indexing run
    logger.info("Starting indexing simulation...")
    
    # Try fetching ALL docs (start=0)
    start = 0 
    end = time.time()
    checkpoint = connector.build_dummy_checkpoint()
    
    count = 0
    try:
        for item in connector.load_from_checkpoint(start, end, checkpoint):
            if isinstance(item, Document):
                count += 1
                logger.info(f"Generated Doc: {item.id} - {item.semantic_identifier[:50]}")
            elif isinstance(item, ConnectorFailure):
                logger.error(f"Failure: {item.failure_message}")
            
            if count >= 5:
                logger.info("Fetched 5 docs, stopping.")
                break
                
        if count == 0:
            logger.warning("⚠️ No documents fetched!")
    except Exception as e:
        logger.error(f"❌ Error during crawling: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_connector()
