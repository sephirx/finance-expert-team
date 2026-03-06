from typing import Any


class MessageBus:
    """
    Shared memory between agents in one session.
    Agents write results here. Other agents read from here.
    Prevents agents from directly calling each other.
    """

    def __init__(self):
        self._store: dict[str, dict] = {}

    def publish(self, agent_name: str, result: dict[str, Any]):
        self._store[agent_name] = result

    def get(self, agent_name: str) -> dict | None:
        return self._store.get(agent_name)

    def get_all(self) -> dict[str, dict]:
        return dict(self._store)

    def clear(self):
        self._store.clear()
