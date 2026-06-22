import logging
import yaml
from pathlib import Path
from brain.memory.sqlite_store import SQLiteStore
from config.settings import settings

logger = logging.getLogger(__name__)
from brain.memory.chroma_store import ChromaStore
from brain.llm_router import LLMRouter


class ContextManager:
    SHAY_CONTEXT_PATH = Path("config/shay_context.yaml")

    def __init__(self) -> None:
        self.sqlite = SQLiteStore()
        self.chroma = ChromaStore()
        self.llm = LLMRouter()
        self._seed_memory_blocks_if_empty()

    def _load_shay_context(self) -> str:
        try:
            with open(self.SHAY_CONTEXT_PATH, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            return yaml.dump(data, default_flow_style=False, allow_unicode=True)
        except FileNotFoundError:
            logger.warning("Context file not found: %s — running without user profile.", self.SHAY_CONTEXT_PATH)
            return ""
        except Exception as e:
            logger.warning("Failed to load context file: %s", e)
            return ""

    def _seed_memory_blocks_if_empty(self) -> None:
        """One-time migration: seed human_block/persona_block from shay_context.yaml
        the first time memory_blocks is empty. Idempotent — does nothing once seeded."""
        if self.sqlite.get_all_blocks("human"):
            return

        raw_yaml = self._load_shay_context()
        if not raw_yaml:
            logger.warning("No shay_context.yaml found — starting with empty memory blocks.")
            return

        try:
            data = yaml.safe_load(raw_yaml) or {}
        except Exception as e:
            logger.warning("Could not parse shay_context.yaml for seeding: %s", e)
            return

        for section in ("identity", "personality", "projects"):
            if section in data:
                content = yaml.dump(data[section], default_flow_style=False, allow_unicode=True)
                self.sqlite.upsert_block("human", section, content, {"source": "shay_context_yaml_seed"})

        if "communication_with_jarvis" in data:
            content = yaml.dump(data["communication_with_jarvis"], default_flow_style=False, allow_unicode=True)
            self.sqlite.upsert_block("persona", "communication_style", content, {"source": "shay_context_yaml_seed"})

        logger.info("Seeded memory_blocks from shay_context.yaml (one-time migration).")

    def _build_system_prompt(self, relevant_memories: list[dict]) -> str:
        human_blocks = self.sqlite.get_all_blocks("human")
        persona_blocks = self.sqlite.get_all_blocks("persona")
        project_blocks = self.sqlite.get_all_blocks("project")

        parts = [
            f"You are JARVIS, {settings.owner_name}'s personal AI assistant. You know him deeply and evolve as you learn more.",
        ]

        if persona_blocks:
            parts.append("\n## How JARVIS Should Behave")
            for b in persona_blocks:
                parts.append(f"### {b['key']}\n{b['content'].strip()}")

        if human_blocks:
            parts.append("\n## Who Shay Is (dynamic — updates as JARVIS learns)")
            for b in human_blocks:
                parts.append(f"### {b['key']}\n{b['content'].strip()}")

        if project_blocks:
            parts.append("\n## Active Projects")
            for b in project_blocks:
                parts.append(f"### {b['key']}\n{b['content'].strip()}")

        if relevant_memories:
            parts.append("\n## Relevant Memories (episodic)")
            for m in relevant_memories:
                parts.append(f"- {m['text']}")

        return "\n".join(parts)

    def _build_history(self, raw: list[dict]) -> list[dict]:
        chronological = list(reversed(raw))
        return [
            {"role": msg["role"], "content": msg["content"]}
            for msg in chronological
            if msg["role"] in ("user", "assistant") and msg.get("interface") != "scheduler"
        ]

    def build_messages(self, user_message: str) -> list[dict]:
        """Build full messages list (system + history + user) for agent_loop."""
        relevant_memories = self.chroma.search_memories(user_message, n_results=3)
        system_prompt = self._build_system_prompt(relevant_memories)
        history = self._build_history(self.sqlite.get_recent_messages(10))
        messages: list[dict] = [{"role": "system", "content": system_prompt}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_message})
        return messages

    async def chat(self, user_message: str, interface: str = "telegram") -> str:
        from tools.search import should_search, search_web

        relevant_memories = self.chroma.search_memories(user_message, n_results=3)
        system_prompt = self._build_system_prompt(relevant_memories)

        if should_search(user_message):
            search_results = await search_web(user_message)
            system_prompt += f"\n\n## Live Web Search Results\n{search_results}"

        history = self._build_history(self.sqlite.get_recent_messages(10))
        self.sqlite.add_message(interface, "user", user_message)

        messages: list[dict] = [{"role": "system", "content": system_prompt}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_message})

        context_tokens = sum(len(m["content"]) // 4 for m in messages)
        response = await self.llm.chat(messages, context_tokens=context_tokens)

        self.sqlite.add_message(interface, "assistant", response)

        from brain.memory.block_updater import maybe_update_human_block
        try:
            await maybe_update_human_block(self, user_message, response)
        except Exception as e:
            logger.warning("block_updater failed (non-fatal): %s", e)

        return response

    def remember(self, fact: str) -> None:
        metadata = {"source": "user_command", "type": "preference"}
        self.chroma.add_memory(fact, metadata)
        key = fact[:60].replace(" ", "_").lower()
        self.sqlite.set_preference(key, fact)

    def get_status(self) -> dict:
        open_tasks = self.sqlite.get_open_tasks()
        preferences = self.sqlite.get_all_preferences()
        total_memories = self.chroma.count()
        recent_prefs = dict(list(preferences.items())[-5:]) if preferences else {}
        return {
            "total_memories": total_memories,
            "open_tasks": open_tasks,
            "recent_preferences": recent_prefs,
        }
