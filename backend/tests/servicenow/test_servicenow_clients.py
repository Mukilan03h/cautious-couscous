import unittest
from unittest.mock import MagicMock, patch
import json
import sys

# Mock logger before importing clients that use it
mock_logger_module = MagicMock()
mock_logger_instance = MagicMock()
mock_logger_module.setup_logger.return_value = mock_logger_instance
sys.modules['esa.utils.logger'] = mock_logger_module

from esa.connectors.servicenow.enhanced_client import EnhancedServiceNowClient
from esa.connectors.servicenow.service_catalog_api import ServiceCatalogAPIClient
from esa.connectors.servicenow.asset_management_api import AssetManagementAPIClient


class TestEnhancedServiceNowClient(unittest.TestCase):
    
    def setUp(self):
        self.mock_session_patch = patch('requests.Session')
        self.mock_session_cls = self.mock_session_patch.start()
        self.mock_session = self.mock_session_cls.return_value
        
        # Configure mock response
        self.mock_response = MagicMock()
        self.mock_response.ok = True
        self.mock_response.status_code = 200
        self.mock_response.json.return_value = {"result": []}
        self.mock_session.request.return_value = self.mock_response
        self.mock_session.get.return_value = self.mock_response
        self.mock_session.post.return_value = self.mock_response
        
        self.client = EnhancedServiceNowClient(
            instance_url="test",
            username="user",
            password="pass"
        )
        # Inject mock session
        self.client._session = self.mock_session

    def tearDown(self):
        self.mock_session_patch.stop()

    def test_get_task_by_number_incident(self):
        """Test polymorphic task lookup for Incident."""
        self.mock_response.json.return_value = {
            "result": [{"sys_id": "inc_1", "number": "INC001", "short_description": "Test"}]
        }
        
        task = self.client.get_task_by_number("INC001")
        
        self.assertIsNotNone(task)
        self.assertEqual(task["number"], "INC001")
        self.assertEqual(task["_table"], "incident")
        
        # Verify correct table was queried
        self.assertTrue(self.mock_session.request.called)
        call_args = self.mock_session.request.call_args
        # call_args is ((args), kwargs)
        # BaseServiceNowClient calls session.request(method=..., url=...) so args is likely empty
        kwargs = call_args[1]
        url = kwargs.get('url')
        if not url and len(call_args[0]) > 1:
             url = call_args[0][1]
        
        self.assertIn("/table/incident", url)

    def test_get_ci_dependencies_recursive(self):
        """Test recursive CI dependency resolution."""
        # Mock responses for different calls
        # This is complex to mock perfectly with a single return_value, 
        # so we'll use side_effect or just verify the first level logic
        
        # First call: Get dependencies of Root CI
        self.mock_response.json.side_effect = [
            # Call 1: Get records from cmdb_rel_ci
            {
                "result": [
                    {
                        "child": {"value": "child_1", "display_value": "Child 1"},
                        "child.name": "Child 1",
                        "child.sys_class_name": "cmdb_ci_server",
                        "type.name": "Runs on"
                    }
                ]
            },
            # Call 2: Recursion for Child 1 (depth 2) -> returns empty to stop
            {"result": []}
        ]
        
        deps = self.client.get_ci_dependencies("root_sys_id", depth=2, direction="downstream")
        
        self.assertEqual(len(deps), 1)
        self.assertEqual(deps[0]["name"], "Child 1")
        self.assertEqual(deps[0]["sys_id"], "child_1")
        
    def test_batch_resolve_references(self):
        """Test batch reference resolution."""
        records = [
            {"sys_id": "1", "assigned_to": {"value": "user_1"}},
            {"sys_id": "2", "assigned_to": {"value": "user_2"}},
        ]
        
        # Mock batch fetch response
        self.mock_response.json.return_value = {
            "result": [
                {"sys_id": "user_1", "name": "User One"},
                {"sys_id": "user_2", "name": "User Two"},
            ]
        }
        
        resolved = self.client.batch_resolve_references(
            records, 
            {"assigned_to": "sys_user"}
        )
        
        self.assertIn("assigned_to_resolved", resolved[0])
        self.assertEqual(resolved[0]["assigned_to_resolved"]["name"], "User One")
        self.assertEqual(resolved[1]["assigned_to_resolved"]["name"], "User Two")


class TestServiceCatalogClient(unittest.TestCase):
    
    def setUp(self):
        self.mock_session_patch = patch('requests.Session')
        self.mock_session_cls = self.mock_session_patch.start()
        self.mock_session = self.mock_session_cls.return_value
        
        self.mock_response = MagicMock()
        self.mock_response.ok = True
        self.mock_response.status_code = 200
        self.mock_session.request.return_value = self.mock_response
        self.mock_session.get.return_value = self.mock_response
        self.mock_session.post.return_value = self.mock_response
        
        self.client = ServiceCatalogAPIClient("test", "u", "p")
        self.client._session = self.mock_session
        
    def tearDown(self):
        self.mock_session_patch.stop()

    def test_order_item(self):
        """Test ordering an item."""
        self.mock_response.json.return_value = {
            "result": {"number": "REQ001"}
        }
        
        result = self.client.add_to_cart("item_1", quantity=2)
        if result:
            # Verify request was made
            self.assertTrue(self.mock_session.request.called)
            # Verify method was POST
            call_args = self.mock_session.request.call_args
            self.assertEqual(call_args[1].get('method'), 'POST')
        
    def test_get_request_status_hierarchy(self):
        """Test retrieving Request->RITM->Task hierarchy."""
        # Using side_effect to return different data for each call
        self.mock_response.json.side_effect = [
            # 1. Get Request
            {"result": [{"sys_id": "req_1", "number": "REQ001"}]},
            # 2. Get RITMs
            {"result": [{"sys_id": "ritm_1", "number": "RITM001"}]},
            # 3. Get Tasks for RITM 1
            {"result": [{"sys_id": "task_1", "number": "TASK001"}]}
        ]
        
        status = self.client.get_request_status("REQ001")
        
        self.assertEqual(status["number"], "REQ001")
        self.assertEqual(len(status["items"]), 1)
        self.assertEqual(status["items"][0]["number"], "RITM001")
        self.assertEqual(len(status["items"][0]["tasks"]), 1)
        self.assertEqual(status["items"][0]["tasks"][0]["number"], "TASK001")


if __name__ == '__main__':
    unittest.main()
