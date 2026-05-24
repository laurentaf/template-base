import asyncio
import json
from datetime import datetime

import redis.asyncio as redis

from src.core.config import settings

HEARTBEAT_TTL = 30
REGISTRY_KEY = "agent:registry"


class AgentRegistry:
    def __init__(self, redis_url: str | None = None):
        self.redis_url = redis_url or settings.REDIS_URL
        self._redis: redis.Redis | None = None

    async def connect(self):
        if self._redis is None:
            self._redis = await redis.from_url(self.redis_url, decode_responses=True)

    async def register(self, agent_id: str, agent_type: str, capabilities: list[str]):
        await self.connect()
        entry = {
            "agent_id": agent_id,
            "agent_type": agent_type,
            "capabilities": capabilities,
            "status": "idle",
            "last_heartbeat": datetime.now().isoformat(),
        }
        await self._redis.hset(REGISTRY_KEY, agent_id, json.dumps(entry))

    async def heartbeat(self, agent_id: str):
        await self.connect()
        entry = await self._redis.hget(REGISTRY_KEY, agent_id)
        if entry:
            data = json.loads(entry)
            data["last_heartbeat"] = datetime.now().isoformat()
            await self._redis.hset(REGISTRY_KEY, agent_id, json.dumps(data))

    async def set_status(self, agent_id: str, status: str):
        await self.connect()
        entry = await self._redis.hget(REGISTRY_KEY, agent_id)
        if entry:
            data = json.loads(entry)
            data["status"] = status
            await self._redis.hset(REGISTRY_KEY, agent_id, json.dumps(data))

    async def discover(self, capability: str | None = None) -> list[dict]:
        await self.connect()
        all_agents = await self._redis.hgetall(REGISTRY_KEY)
        result = []
        for agent_id, entry in all_agents.items():
            data = json.loads(entry)
            # Prune stale agents
            last = datetime.fromisoformat(data["last_heartbeat"])
            if (datetime.now() - last).seconds > HEARTBEAT_TTL:
                await self._redis.hdel(REGISTRY_KEY, agent_id)
                continue
            if capability and capability not in data.get("capabilities", []):
                continue
            data["agent_id"] = agent_id
            result.append(data)
        return result

    async def find_idle(self, agent_type: str) -> dict | None:
        agents = await self.discover()
        for a in agents:
            if a["agent_type"] == agent_type and a.get("status") == "idle":
                return a
        return None

    async def unregister(self, agent_id: str):
        await self.connect()
        await self._redis.hdel(REGISTRY_KEY, agent_id)

    async def start_heartbeat_loop(self, agent_id: str, interval: int = 15):
        while True:
            await self.heartbeat(agent_id)
            await asyncio.sleep(interval)
