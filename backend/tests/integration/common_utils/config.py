import generated.esa_openapi_client.esa_openapi_client as esa_api  # type: ignore[import]
from tests.integration.common_utils.constants import API_SERVER_URL

api_config = esa_api.Configuration(host=API_SERVER_URL)
