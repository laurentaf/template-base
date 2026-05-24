import asyncio
import uuid
from collections import defaultdict
from datetime import datetime

from src.core.agent_registry import HEARTBEAT_TTL


class LocalTaskQueue:
    def __init__(self):
        self._queue: asyncio.Queue = asyncio.Queue()
        self._pending: dict[str, dict] = {}

    async def connect(self):
        pass

    async def enqueue(self, task_type: str, payload: dict, priority: int = 0) -> str:
        msg_id = str(uuid.uuid4())
        entry = {"msg_id": msg_id, "type": task_type, "payload": payload, "priority": priority}
        self._pending[msg_id] = entry
        await self._queue.put(entry)
        return msg_id

    async def dequeue(self, consumer_id: str, timeout: int = 5) -> dict | None:
        try:
            return await asyncio.wait_for(self._queue.get(), timeout=timeout)
        except TimeoutError:
            return None

    async def acknowledge(self, msg_id: str):
        self._pending.pop(msg_id, None)

    async def nack(self, msg_id: str):
        entry = self._pending.pop(msg_id, None)
        if entry:
            await self._queue.put(entry)

    async def pending_count(self) -> int:
        return self._queue.qsize()


class LocalMessageBus:
    def __init__(self):
        self._handlers: dict[str, list] = defaultdict(list)
        self._running = True

    async def connect(self):
        pass

    async def publish(self, channel: str, message: dict):
        for handler in self._handlers.get(channel, []):
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(message)
                else:
                    handler(message)
            except Exception:
                pass

    def subscribe(self, channel: str, handler):
        self._handlers[channel].append(handler)

    async def listen(self, channels: list[str]):
        keepalive = asyncio.get_running_loop().create_future()
        try:
            await keepalive
        except asyncio.CancelledError:
            pass

    async def close(self):
        self._running = False


class LocalDistributedState:
    def __init__(self):
        self._data: dict[str, dict] = {}
        self._lock = asyncio.Lock()

    async def connect(self):
        pass

    async def disconnect(self):
        self._data.clear()

    async def get_state(self, key: str) -> dict | None:
        raw = self._data.get(f"state:{key}")
        return dict(raw) if raw else None

    async def set_state(self, key: str, value: dict, version: int | None = None):
        state_key = f"state:{key}"
        async with self._lock:
            current = self._data.get(state_key)
            if version is not None and current and current.get("version", 0) != version:
                expected, got = version, current.get("version", 0)
                raise ValueError(
                    f"Version conflict for {key}: expected {expected}, got {got}"
                )
            value["version"] = (current.get("version", 0) if current else 0) + 1
            self._data[state_key] = dict(value)

    async def update_state(self, key: str, delta: dict):
        state_key = f"state:{key}"
        async with self._lock:
            current = self._data.get(state_key, {})
            current.update(delta)
            current["version"] = current.get("version", 0) + 1
            self._data[state_key] = current

    async def delete_state(self, key: str):
        self._data.pop(f"state:{key}", None)

    async def list_keys(self, prefix: str = "") -> list[str]:
        pattern = f"state:{prefix}" if prefix else "state:"
        return [k.replace("state:", "") for k in self._data if k.startswith(pattern)]


class LocalAgentRegistry:
    def __init__(self):
        self._agents: dict[str, dict] = {}

    async def connect(self):
        pass

    async def register(self, agent_id: str, agent_type: str, capabilities: list[str]):
        self._agents[agent_id] = {
            "agent_id": agent_id,
            "agent_type": agent_type,
            "capabilities": capabilities,
            "status": "idle",
            "last_heartbeat": datetime.now().isoformat(),
        }

    async def heartbeat(self, agent_id: str):
        entry = self._agents.get(agent_id)
        if entry:
            entry["last_heartbeat"] = datetime.now().isoformat()

    async def set_status(self, agent_id: str, status: str):
        entry = self._agents.get(agent_id)
        if entry:
            entry["status"] = status

    async def discover(self, capability: str | None = None) -> list[dict]:
        now = datetime.now()
        result = []
        to_remove = []
        for agent_id, data in self._agents.items():
            last = datetime.fromisoformat(data["last_heartbeat"])
            if (now - last).seconds > HEARTBEAT_TTL:
                to_remove.append(agent_id)
                continue
            if capability and capability not in data.get("capabilities", []):
                continue
            result.append(dict(data))
        for rid in to_remove:
            self._agents.pop(rid, None)
        return result

    async def find_idle(self, agent_type: str) -> dict | None:
        agents = await self.discover()
        for a in agents:
            if a["agent_type"] == agent_type and a.get("status") == "idle":
                return a
        return None

    async def unregister(self, agent_id: str):
        self._agents.pop(agent_id, None)


async def check_redis(redis_url: str | None = None, timeout: float = 2.0) -> bool:
    from src.core.config import settings as _settings

    url = redis_url or _settings.REDIS_URL
    try:
        import redis.asyncio as redis

        r = await redis.from_url(url, decode_responses=True, socket_connect_timeout=timeout)
        await r.ping()
        await r.close()
        return True
    except Exception:
        return False
