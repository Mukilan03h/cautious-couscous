import logging
import sys
import traceback
import warnings
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any
from typing import cast

import sentry_sdk
import uvicorn
from fastapi import APIRouter
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import Request
from fastapi import status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from httpx_oauth.clients.google import GoogleOAuth2
from httpx_oauth.clients.openid import BASE_SCOPES
from httpx_oauth.clients.openid import OpenID
from prometheus_fastapi_instrumentator import Instrumentator
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration
from starlette.types import Lifespan

from esa import __version__
from esa.auth.schemas import UserCreate
from esa.auth.schemas import UserRead
from esa.auth.schemas import UserUpdate
from esa.auth.users import auth_backend
from esa.auth.users import create_esa_oauth_router
from esa.auth.users import fastapi_users
from esa.configs.app_configs import APP_API_PREFIX
from esa.configs.app_configs import APP_HOST
from esa.configs.app_configs import APP_PORT
from esa.configs.app_configs import AUTH_RATE_LIMITING_ENABLED
from esa.configs.app_configs import AUTH_TYPE
from esa.configs.app_configs import DISABLE_GENERATIVE_AI
from esa.configs.app_configs import LOG_ENDPOINT_LATENCY
from esa.configs.app_configs import OAUTH_CLIENT_ID
from esa.configs.app_configs import OAUTH_CLIENT_SECRET
from esa.configs.app_configs import OIDC_SCOPE_OVERRIDE
from esa.configs.app_configs import OPENID_CONFIG_URL
from esa.configs.app_configs import POSTGRES_API_SERVER_POOL_OVERFLOW
from esa.configs.app_configs import POSTGRES_API_SERVER_POOL_SIZE
from esa.configs.app_configs import POSTGRES_API_SERVER_READ_ONLY_POOL_OVERFLOW
from esa.configs.app_configs import POSTGRES_API_SERVER_READ_ONLY_POOL_SIZE
from esa.configs.app_configs import SYSTEM_RECURSION_LIMIT
from esa.configs.app_configs import USER_AUTH_SECRET
from esa.configs.app_configs import WEB_DOMAIN
from esa.configs.constants import AuthType
from esa.configs.constants import POSTGRES_WEB_APP_NAME
from esa.db.engine.connection_warmup import warm_up_connections
from esa.db.engine.sql_engine import get_session_with_current_tenant
from esa.db.engine.sql_engine import SqlEngine
from esa.file_store.file_store import get_default_file_store
from esa.server.api_key.api import router as api_key_router
from esa.server.auth_check import check_router_auth
from esa.server.documents.cc_pair import router as cc_pair_router
from esa.server.documents.connector import router as connector_router
from esa.server.documents.credential import router as credential_router
from esa.server.documents.document import router as document_router
from esa.server.documents.standard_oauth import router as standard_oauth_router
from esa.server.features.default_assistant.api import (
    router as default_assistant_router,
)
from esa.server.features.document_set.api import router as document_set_router
from esa.server.features.input_prompt.api import (
    admin_router as admin_input_prompt_router,
)
from esa.server.features.input_prompt.api import (
    basic_router as input_prompt_router,
)
from esa.server.features.mcp.api import admin_router as mcp_admin_router
from esa.server.features.mcp.api import router as mcp_router
from esa.server.features.notifications.api import router as notification_router
from esa.server.features.oauth_config.api import (
    admin_router as admin_oauth_config_router,
)
from esa.server.features.oauth_config.api import router as oauth_config_router
from esa.server.features.password.api import router as password_router
from esa.server.features.persona.api import admin_agents_router
from esa.server.features.persona.api import admin_router as admin_persona_router
from esa.server.features.persona.api import agents_router
from esa.server.features.persona.api import basic_router as persona_router
from esa.server.features.projects.api import router as projects_router
from esa.server.features.tool.api import admin_router as admin_tool_router
from esa.server.features.tool.api import router as tool_router
from esa.server.features.user_oauth_token.api import router as user_oauth_token_router
from esa.server.features.web_search.api import router as web_search_router
from esa.server.federated.api import router as federated_router
from esa.server.kg.api import admin_router as kg_admin_router
from esa.server.long_term_logs.long_term_logs_api import (
    router as long_term_logs_router,
)
from esa.server.manage.administrative import router as admin_router
from esa.server.manage.embedding.api import admin_router as embedding_admin_router
from esa.server.manage.embedding.api import basic_router as embedding_router
from esa.server.manage.get_state import router as state_router
from esa.server.manage.llm.api import admin_router as llm_admin_router
from esa.server.manage.llm.api import basic_router as llm_router
from esa.server.manage.search_settings import router as search_settings_router
from esa.server.manage.slack_bot import router as slack_bot_management_router
from esa.server.manage.users import router as user_router
from esa.server.manage.web_search.api import (
    admin_router as web_search_admin_router,
)
from esa.server.middleware.latency_logging import add_latency_logging_middleware
from esa.server.middleware.rate_limiting import close_auth_limiter
from esa.server.middleware.rate_limiting import get_auth_rate_limiters
from esa.server.middleware.rate_limiting import setup_auth_limiter
from esa.server.esa_api.ingestion import router as esa_api_router
from esa.server.pat.api import router as pat_router
from esa.server.query_and_chat.chat_backend import router as chat_router
from esa.server.query_and_chat.chat_backend_v0 import router as chat_v0_router
from esa.server.query_and_chat.query_backend import (
    admin_router as admin_query_router,
)
from esa.server.query_and_chat.query_backend import basic_router as query_router
from esa.server.saml import router as saml_router
from esa.server.settings.api import admin_router as settings_admin_router
from esa.server.settings.api import basic_router as settings_router
from esa.server.token_rate_limits.api import (
    router as token_rate_limit_settings_router,
)
from esa.server.utils import BasicAuthenticationError
from esa.setup import setup_multitenant_esa
from esa.setup import setup_esa
from esa.tracing.braintrust_tracing import setup_braintrust_if_creds_available
from esa.tracing.langfuse_tracing import setup_langfuse_if_creds_available
from esa.utils.logger import setup_logger
from esa.utils.logger import setup_uvicorn_logger
from esa.utils.middleware import add_esa_request_id_middleware
from esa.utils.telemetry import get_or_generate_uuid
from esa.utils.telemetry import optional_telemetry
from esa.utils.telemetry import RecordType
from esa.utils.variable_functionality import fetch_versioned_implementation
from esa.utils.variable_functionality import global_version
from esa.utils.variable_functionality import set_is_ee_based_on_env_variable
from shared_configs.configs import CORS_ALLOWED_ORIGIN
from shared_configs.configs import MULTI_TENANT
from shared_configs.configs import POSTGRES_DEFAULT_SCHEMA
from shared_configs.configs import SENTRY_DSN
from shared_configs.contextvars import CURRENT_TENANT_ID_CONTEXTVAR

warnings.filterwarnings(
    "ignore", category=ResourceWarning, message=r"Unclosed client session"
)
warnings.filterwarnings(
    "ignore", category=ResourceWarning, message=r"Unclosed connector"
)

logger = setup_logger()

file_handlers = [
    h for h in logger.logger.handlers if isinstance(h, logging.FileHandler)
]

setup_uvicorn_logger(shared_file_handlers=file_handlers)


def validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, RequestValidationError):
        logger.error(
            f"Unexpected exception type in validation_exception_handler - {type(exc)}"
        )
        raise exc

    exc_str = f"{exc}".replace("\n", " ").replace("   ", " ")
    logger.exception(f"{request}: {exc_str}")
    content = {"status_code": 422, "message": exc_str, "data": None}
    return JSONResponse(content=content, status_code=422)


def value_error_handler(_: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, ValueError):
        logger.error(f"Unexpected exception type in value_error_handler - {type(exc)}")
        raise exc

    try:
        raise (exc)
    except Exception:
        # log stacktrace
        logger.exception("ValueError")
    return JSONResponse(
        status_code=400,
        content={"message": str(exc)},
    )


def use_route_function_names_as_operation_ids(app: FastAPI) -> None:
    """
    OpenAPI generation defaults to naming the operation with the
    function + route + HTTP method, which usually looks very redundant.

    This function changes the operation IDs to be just the function name.

    Should be called only after all routes have been added.
    """
    for route in app.routes:
        if isinstance(route, APIRoute):
            route.operation_id = route.name


def include_router_with_global_prefix_prepended(
    application: FastAPI, router: APIRouter, **kwargs: Any
) -> None:
    """Adds the global prefix to all routes in the router."""
    processed_global_prefix = f"/{APP_API_PREFIX.strip('/')}" if APP_API_PREFIX else ""

    passed_in_prefix = cast(str | None, kwargs.get("prefix"))
    if passed_in_prefix:
        final_prefix = f"{processed_global_prefix}/{passed_in_prefix.strip('/')}"
    else:
        final_prefix = f"{processed_global_prefix}"
    final_kwargs: dict[str, Any] = {
        **kwargs,
        "prefix": final_prefix,
    }

    application.include_router(router, **final_kwargs)


def include_auth_router_with_prefix(
    application: FastAPI,
    router: APIRouter,
    prefix: str | None = None,
    tags: list[str] | None = None,
) -> None:
    """Wrapper function to include an 'auth' router with prefix + rate-limiting dependencies."""
    final_tags = tags or ["auth"]
    include_router_with_global_prefix_prepended(
        application,
        router,
        prefix=prefix,
        tags=final_tags,
        dependencies=get_auth_rate_limiters(),
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Set recursion limit
    if SYSTEM_RECURSION_LIMIT is not None:
        sys.setrecursionlimit(SYSTEM_RECURSION_LIMIT)
        logger.notice(f"System recursion limit set to {SYSTEM_RECURSION_LIMIT}")

    SqlEngine.set_app_name(POSTGRES_WEB_APP_NAME)

    SqlEngine.init_engine(
        pool_size=POSTGRES_API_SERVER_POOL_SIZE,
        max_overflow=POSTGRES_API_SERVER_POOL_OVERFLOW,
    )
    SqlEngine.get_engine()

    SqlEngine.init_readonly_engine(
        pool_size=POSTGRES_API_SERVER_READ_ONLY_POOL_SIZE,
        max_overflow=POSTGRES_API_SERVER_READ_ONLY_POOL_OVERFLOW,
    )

    verify_auth = fetch_versioned_implementation(
        "esa.auth.users", "verify_auth_setting"
    )

    # Will throw exception if an issue is found
    verify_auth()

    if OAUTH_CLIENT_ID and OAUTH_CLIENT_SECRET:
        logger.notice("Both OAuth Client ID and Secret are configured.")

    if DISABLE_GENERATIVE_AI:
        logger.notice("Generative AI Q&A disabled")

    # Initialize tracing if credentials are provided
    setup_braintrust_if_creds_available()
    setup_langfuse_if_creds_available()

    # fill up Postgres connection pools
    await warm_up_connections()

    if not MULTI_TENANT:
        # We cache this at the beginning so there is no delay in the first telemetry
        CURRENT_TENANT_ID_CONTEXTVAR.set(POSTGRES_DEFAULT_SCHEMA)
        get_or_generate_uuid()

        # If we are multi-tenant, we need to only set up initial public tables
        with get_session_with_current_tenant() as db_session:
            setup_esa(db_session, POSTGRES_DEFAULT_SCHEMA)
            # set up the file store (e.g. create bucket if needed). On multi-tenant,
            # this is done via IaC
            try:
                get_default_file_store().initialize()
            except Exception as e:
                logger.warning(f"File store initialization failed (S3/AWS not configured): {e}")
                logger.notice("Backend will continue without file storage. File upload features may be limited.")
    else:
        setup_multitenant_esa()

    if not MULTI_TENANT:
        # don't emit a metric for every pod rollover/restart
        optional_telemetry(
            record_type=RecordType.VERSION, data={"version": __version__}
        )

    if AUTH_RATE_LIMITING_ENABLED:
        await setup_auth_limiter()

    yield

    SqlEngine.reset_engine()

    if AUTH_RATE_LIMITING_ENABLED:
        await close_auth_limiter()


def log_http_error(request: Request, exc: Exception) -> JSONResponse:
    status_code = getattr(exc, "status_code", 500)

    if isinstance(exc, BasicAuthenticationError):
        # For BasicAuthenticationError, just log a brief message without stack trace
        # (almost always spammy)
        logger.debug(f"Authentication failed: {str(exc)}")

    elif status_code == 404 and request.url.path == "/metrics":
        # Log 404 errors for the /metrics endpoint with debug level
        logger.debug(f"404 error for /metrics endpoint: {str(exc)}")

    elif status_code >= 400:
        error_msg = f"{str(exc)}\n"
        error_msg += "".join(traceback.format_tb(exc.__traceback__))
        logger.error(error_msg)

    detail = exc.detail if isinstance(exc, HTTPException) else str(exc)
    return JSONResponse(
        status_code=status_code,
        content={"detail": detail},
    )


def get_application(lifespan_override: Lifespan | None = None) -> FastAPI:
    application = FastAPI(
        title="ESA Backend",
        version=__version__,
        description="ESA API for AI-powered chat with search, document indexing, agents, actions, and more",
        servers=[
            {"url": f"{WEB_DOMAIN.rstrip('/')}/api", "description": "ESA API Server"}
        ],
        lifespan=lifespan_override or lifespan,
    )
    if SENTRY_DSN:
        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=[StarletteIntegration(), FastApiIntegration()],
            traces_sample_rate=0.1,
        )
        logger.info("Sentry initialized")
    else:
        logger.debug("Sentry DSN not provided, skipping Sentry initialization")

    application.add_exception_handler(status.HTTP_400_BAD_REQUEST, log_http_error)
    application.add_exception_handler(status.HTTP_401_UNAUTHORIZED, log_http_error)
    application.add_exception_handler(status.HTTP_403_FORBIDDEN, log_http_error)
    application.add_exception_handler(status.HTTP_404_NOT_FOUND, log_http_error)
    application.add_exception_handler(
        status.HTTP_500_INTERNAL_SERVER_ERROR, log_http_error
    )

    include_router_with_global_prefix_prepended(application, password_router)
    include_router_with_global_prefix_prepended(application, chat_router)
    include_router_with_global_prefix_prepended(application, chat_v0_router)
    include_router_with_global_prefix_prepended(application, query_router)
    include_router_with_global_prefix_prepended(application, document_router)
    include_router_with_global_prefix_prepended(application, user_router)
    include_router_with_global_prefix_prepended(application, admin_query_router)
    include_router_with_global_prefix_prepended(application, admin_router)
    include_router_with_global_prefix_prepended(application, connector_router)
    include_router_with_global_prefix_prepended(application, credential_router)
    include_router_with_global_prefix_prepended(application, input_prompt_router)
    include_router_with_global_prefix_prepended(application, admin_input_prompt_router)
    include_router_with_global_prefix_prepended(application, cc_pair_router)
    include_router_with_global_prefix_prepended(application, projects_router)
    include_router_with_global_prefix_prepended(application, document_set_router)
    include_router_with_global_prefix_prepended(application, search_settings_router)
    include_router_with_global_prefix_prepended(
        application, slack_bot_management_router
    )
    include_router_with_global_prefix_prepended(application, persona_router)
    include_router_with_global_prefix_prepended(application, admin_persona_router)
    include_router_with_global_prefix_prepended(application, agents_router)
    include_router_with_global_prefix_prepended(application, admin_agents_router)
    include_router_with_global_prefix_prepended(application, default_assistant_router)
    include_router_with_global_prefix_prepended(application, notification_router)
    include_router_with_global_prefix_prepended(application, tool_router)
    include_router_with_global_prefix_prepended(application, admin_tool_router)
    include_router_with_global_prefix_prepended(application, oauth_config_router)
    include_router_with_global_prefix_prepended(application, admin_oauth_config_router)
    include_router_with_global_prefix_prepended(application, user_oauth_token_router)
    include_router_with_global_prefix_prepended(application, state_router)
    include_router_with_global_prefix_prepended(application, esa_api_router)
    include_router_with_global_prefix_prepended(application, settings_router)
    include_router_with_global_prefix_prepended(application, settings_admin_router)
    include_router_with_global_prefix_prepended(application, llm_admin_router)
    include_router_with_global_prefix_prepended(application, kg_admin_router)
    include_router_with_global_prefix_prepended(application, llm_router)
    include_router_with_global_prefix_prepended(application, embedding_admin_router)
    include_router_with_global_prefix_prepended(application, embedding_router)
    include_router_with_global_prefix_prepended(application, web_search_router)
    include_router_with_global_prefix_prepended(application, web_search_admin_router)
    include_router_with_global_prefix_prepended(
        application, token_rate_limit_settings_router
    )
    include_router_with_global_prefix_prepended(application, long_term_logs_router)
    include_router_with_global_prefix_prepended(application, api_key_router)
    include_router_with_global_prefix_prepended(application, standard_oauth_router)
    include_router_with_global_prefix_prepended(application, federated_router)
    include_router_with_global_prefix_prepended(application, mcp_router)
    include_router_with_global_prefix_prepended(application, mcp_admin_router)

    # ======== Custom Enterprise Features (Your Code) ========
    # These replace ESA EE features with your own implementation
    try:
        # P1: Core
        from myplatform.server.rbac.api import router as custom_rbac_router
        from myplatform.server.analytics.api import router as custom_analytics_router
        from myplatform.server.query_history.api import router as custom_query_history_router
        from myplatform.server.token_limits.api import router as custom_token_limits_router
        from myplatform.server.token_limits.api import user_router as custom_token_usage_router
        from myplatform.server.standard_answers.api import router as custom_std_answers_router
        
        # P2: Permissions
        from myplatform.server.permissions.api import router as custom_permissions_router
        from myplatform.server.permissions.api import user_router as custom_access_router
        
        # P3: Connector Sync
        from myplatform.server.connector_sync.api import router as custom_connector_sync_router
        
        # P4: Multi-Tenancy
        from myplatform.server.tenants.api import router as custom_tenants_router
        from myplatform.server.tenants.api import user_router as custom_my_tenants_router
        
        # P5: Advanced
        from myplatform.server.feature_flags.api import router as custom_feature_flags_router
        from myplatform.server.feature_flags.api import user_router as custom_features_router
        from myplatform.server.evals.api import router as custom_evals_router
        
        # Register all routers
        include_router_with_global_prefix_prepended(application, custom_rbac_router)
        include_router_with_global_prefix_prepended(application, custom_analytics_router)
        include_router_with_global_prefix_prepended(application, custom_query_history_router)
        include_router_with_global_prefix_prepended(application, custom_token_limits_router)
        include_router_with_global_prefix_prepended(application, custom_token_usage_router)
        include_router_with_global_prefix_prepended(application, custom_std_answers_router)
        include_router_with_global_prefix_prepended(application, custom_permissions_router)
        include_router_with_global_prefix_prepended(application, custom_access_router)
        include_router_with_global_prefix_prepended(application, custom_connector_sync_router)
        include_router_with_global_prefix_prepended(application, custom_tenants_router)
        include_router_with_global_prefix_prepended(application, custom_my_tenants_router)
        include_router_with_global_prefix_prepended(application, custom_feature_flags_router)
        include_router_with_global_prefix_prepended(application, custom_features_router)
        include_router_with_global_prefix_prepended(application, custom_evals_router)
        
        logger.notice("Custom enterprise features loaded (P1-P5: RBAC, Analytics, Query History, Token Limits, Standard Answers, Permissions, Connector Sync, Tenants, Feature Flags, Evals)")
    except ImportError as e:
        logger.debug(f"Custom enterprise features not available: {e}")

    if AUTH_TYPE != AuthType.DISABLED:
        include_router_with_global_prefix_prepended(application, pat_router)

    if AUTH_TYPE == AuthType.BASIC or AUTH_TYPE == AuthType.CLOUD:
        include_auth_router_with_prefix(
            application,
            fastapi_users.get_auth_router(auth_backend),
            prefix="/auth",
        )

        include_auth_router_with_prefix(
            application,
            fastapi_users.get_register_router(UserRead, UserCreate),
            prefix="/auth",
        )

        include_auth_router_with_prefix(
            application,
            fastapi_users.get_reset_password_router(),
            prefix="/auth",
        )
        include_auth_router_with_prefix(
            application,
            fastapi_users.get_verify_router(UserRead),
            prefix="/auth",
        )
        include_auth_router_with_prefix(
            application,
            fastapi_users.get_users_router(UserRead, UserUpdate),
            prefix="/users",
        )

    if AUTH_TYPE == AuthType.GOOGLE_OAUTH:
        # For Google OAuth, refresh tokens are requested by:
        # 1. Adding the right scopes
        # 2. Properly configuring OAuth in Google Cloud Console to allow offline access
        oauth_client = GoogleOAuth2(
            OAUTH_CLIENT_ID,
            OAUTH_CLIENT_SECRET,
            # Use standard scopes that include profile and email
            scopes=["openid", "email", "profile"],
        )
        include_auth_router_with_prefix(
            application,
            create_esa_oauth_router(
                oauth_client,
                auth_backend,
                USER_AUTH_SECRET,
                associate_by_email=True,
                is_verified_by_default=True,
                # Points the user back to the login page
                redirect_url=f"{WEB_DOMAIN}/auth/oauth/callback",
            ),
            prefix="/auth/oauth",
        )

        # Need basic auth router for `logout` endpoint
        include_auth_router_with_prefix(
            application,
            fastapi_users.get_logout_router(auth_backend),
            prefix="/auth",
        )

    if AUTH_TYPE == AuthType.OIDC:
        # Ensure we request offline_access for refresh tokens
        try:
            oidc_scopes = list(OIDC_SCOPE_OVERRIDE or BASE_SCOPES)
            if "offline_access" not in oidc_scopes:
                oidc_scopes.append("offline_access")
        except Exception as e:
            logger.warning(f"Error configuring OIDC scopes: {e}")
            # Fall back to default scopes if there's an error
            oidc_scopes = BASE_SCOPES

        include_auth_router_with_prefix(
            application,
            create_esa_oauth_router(
                OpenID(
                    OAUTH_CLIENT_ID,
                    OAUTH_CLIENT_SECRET,
                    OPENID_CONFIG_URL,
                    # Use the configured scopes
                    base_scopes=oidc_scopes,
                ),
                auth_backend,
                USER_AUTH_SECRET,
                associate_by_email=True,
                is_verified_by_default=True,
                redirect_url=f"{WEB_DOMAIN}/auth/oidc/callback",
            ),
            prefix="/auth/oidc",
        )

        # need basic auth router for `logout` endpoint
        include_auth_router_with_prefix(
            application,
            fastapi_users.get_auth_router(auth_backend),
            prefix="/auth",
        )

    elif AUTH_TYPE == AuthType.SAML:
        include_auth_router_with_prefix(
            application,
            saml_router,
        )

    if (
        AUTH_TYPE == AuthType.CLOUD
        or AUTH_TYPE == AuthType.BASIC
        or AUTH_TYPE == AuthType.GOOGLE_OAUTH
        or AUTH_TYPE == AuthType.OIDC
    ):
        # Add refresh token endpoint for OAuth as well
        include_auth_router_with_prefix(
            application,
            fastapi_users.get_refresh_router(auth_backend),
            prefix="/auth",
        )

    application.add_exception_handler(
        RequestValidationError, validation_exception_handler
    )

    application.add_exception_handler(ValueError, value_error_handler)

    application.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ALLOWED_ORIGIN,  # Configurable via environment variable
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    if LOG_ENDPOINT_LATENCY:
        add_latency_logging_middleware(application, logger)

    add_esa_request_id_middleware(application, "API", logger)

    # Ensure all routes have auth enabled or are explicitly marked as public
    check_router_auth(application)

    # Initialize and instrument the app
    Instrumentator().instrument(application).expose(application)

    use_route_function_names_as_operation_ids(application)

    return application


# NOTE: needs to be outside of the `if __name__ == "__main__"` block so that the
# app is exportable
set_is_ee_based_on_env_variable()
app = fetch_versioned_implementation(module="esa.main", attribute="get_application")


if __name__ == "__main__":
    logger.notice(
        f"Starting ESA Backend version {__version__} on http://{APP_HOST}:{str(APP_PORT)}/"
    )

    if global_version.is_ee_version():
        logger.notice("Running Enterprise Edition")

    uvicorn.run(app, host=APP_HOST, port=APP_PORT)
