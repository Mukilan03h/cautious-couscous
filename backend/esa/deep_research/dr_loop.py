from collections.abc import Callable

from sqlalchemy.orm import Session

from esa.chat.chat_state import ChatStateContainer
from esa.chat.emitter import Emitter
from esa.chat.models import ChatMessageSimple
from esa.llm.interfaces import LLM
from esa.tools.tool import Tool
from esa.utils.logger import setup_logger

logger = setup_logger()


def run_deep_research_llm_loop(
    emitter: Emitter,
    state_container: ChatStateContainer,
    simple_chat_history: list[ChatMessageSimple],
    tools: list[Tool],
    custom_agent_prompt: str | None,
    llm: LLM,
    token_counter: Callable[[str], int],
    db_session: Session,
) -> None:
    if llm.config.max_input_tokens < 25000:
        raise RuntimeError(
            "Cannot run Deep Research with an LLM that has less than 25,000 max input tokens"
        )
