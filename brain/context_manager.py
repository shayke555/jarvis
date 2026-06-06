import yaml
from pathlib import Path
from brain.memory.sqlite_store import SQLiteStore
from brain.memory.chroma_store import ChromaStore
from brain.llm_router import LLMRouter


class ContextManager:
    SHAY_CONTEXT_PATH = Path("config/shay_context.yaml")

    def __init__(self) -> None:
        self.sqlite = SQLiteStore()
        self.chroma = ChromaStore()
        self.llm = LLMRouter()
        self._shay_context = self._load_shay_context()

    def _load_shay_context(self) -> str:
        with open(self.SHAY_CONTEXT_PATH, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return yaml.dump(data, default_flow_style=False, allow_unicode=True)

    def _build_system_prompt(self, relevant_memories: list[dict], preferences: dict[str, str]) -> str:
        parts = [
            "You are JARVIS, Shay's personal AI assistant. You know Shay deeply.",
            "",
            "## Shay's Profile",
            "```yaml",
            self._shay_context.strip(),
            "```",
        ]

        if relevant_memories:
            parts.append("\n## Relevant Memories")
            for m in relevant_memories:
                parts.append(f"- {m['text']}")

        if preferences:
            parts.append("\n## Shay's Preferences")
            for key, value in preferences.items():
                parts.append(f"- {key}: {value}")

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
        preferences = self.sqlite.get_all_preferences()
        system_prompt = self._build_system_prompt(relevant_memories, preferences)
        history = self._build_history(self.sqlite.get_recent_messages(10))
        messages: list[dict] = [{"role": "system", "content": system_prompt}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_message})
        return messages

    async def chat(self, user_message: str, interface: str = "telegram") -> str:
        from tools.search import should_search, search_web

        relevant_memories = self.chroma.search_memories(user_message, n_results=3)
        preferences = self.sqlite.get_all_preferences()
        system_prompt = self._build_system_prompt(relevant_memories, preferences)

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
