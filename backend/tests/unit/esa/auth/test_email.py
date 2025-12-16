import pytest

from esa.auth.email_utils import build_user_email_invite
from esa.auth.email_utils import send_email
from esa.configs.constants import AuthType
from esa.configs.constants import ONYX_DEFAULT_APPLICATION_NAME
from esa.db.engine.sql_engine import SqlEngine
from esa.server.runtime.esa_runtime import ESARuntime


@pytest.mark.skip(
    reason="This sends real emails, so only run when you really want to test this!"
)
def test_send_user_email_invite() -> None:
    SqlEngine.init_engine(pool_size=20, max_overflow=5)

    application_name = ONYX_DEFAULT_APPLICATION_NAME

    esa_file = ESARuntime.get_emailable_logo()

    subject = f"Invitation to Join {application_name} Organization"

    FROM_EMAIL = "noreply@esa.app"
    TO_EMAIL = "support@esa.app"
    text_content, html_content = build_user_email_invite(
        FROM_EMAIL, TO_EMAIL, ONYX_DEFAULT_APPLICATION_NAME, AuthType.CLOUD
    )

    send_email(
        TO_EMAIL,
        subject,
        html_content,
        text_content,
        mail_from=FROM_EMAIL,
        inline_png=("logo.png", esa_file.data),
    )
