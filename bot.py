import asyncio
import logging

from dotenv import load_dotenv
load_dotenv(override=True)

from brain.agent_loop import AgentLoop
from brain.context_manager import ContextManager
from brain.llm_router import LLMRouter
from brain.task_brain import init_task_brain, get_tasks
from connectors.registry import register
from interfaces.telegram_bot import run_telegram_bot, set_context_manager, set_agent_loop
from scheduler.daily_briefing import create_scheduler, send_telegram_message
from scheduler.weekly_learning import weekly_learning_job
from scheduler.proactive_nudge import proactive_nudge_job
from tools.registry import ToolRegistry

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    init_task_brain()
    register("tasks", get_tasks)

    cm = ContextManager()
    set_context_manager(cm)

    llm = LLMRouter()
    registry = ToolRegistry()
    agent = AgentLoop(llm=llm, registry=registry)
    set_agent_loop(agent)

    scheduler = create_scheduler(cm)
    scheduler.add_job(
        weekly_learning_job,
        "cron",
        day_of_week="sun",
        hour=8,
        minute=0,
        id="weekly_learning",
    )
    scheduler.add_job(
        proactive_nudge_job,
        "cron",
        hour=9,
        minute=0,
        id="proactive_nudge",
        args=[cm, send_telegram_message],
    )
    scheduler.start()
    logger.info("JARVIS starting — Telegram + AgentLoop + TaskBrain online.")

    try:
        await run_telegram_bot()
    finally:
        scheduler.shutdown()
        logger.info("JARVIS stopped.")


if __name__ == "__main__":
    asyncio.run(main())
