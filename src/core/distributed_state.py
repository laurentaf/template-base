import json

import redis.asyncio as redis


class DistributedStateManager:
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self._redis: redis.Redis | None = None

    async def connect(self):
        if self._redis is None:
            self._redis = await redis.from_url(self.redis_url, decode_responses=True)

    async def disconnect(self):
        if self._redis:
            await self._redis.close()
            self._redis = None

    async def get_state(self, key: str) -> dict | None:
        await self.connect()
        raw = await self._redis.get(f"state:{key}")
        return json.loads(raw) if raw else None

    async def set_state(self, key: str, value: dict, version: int | None = None):
        await self.connect()
        state_key = f"state:{key}"
        if version is not None:
            current = await self.get_state(key)
            if current and current.get("version", 0) != version:
                raise ValueError(
                    f"Version conflict for {key}: expected {version}, got {current.get('version', 0)}"
                )
            value["version"] = (current.get("version", 0) if current else 0) + 1
            async with self._redis.pipeline(transaction=True) as pipe:
                await pipe.watch(state_key)
                await pipe.multi()
                await pipe.set(state_key, json.dumps(value))
                await pipe.execute()
        else:
            value["version"] = value.get("version", 0) + 1
            await self._redis.set(state_key, json.dumps(value))

    async def update_state(self, key: str, delta: dict):
        await self.connect()
        state_key = f"state:{key}"
        current = await self.get_state(key) or {}
        current.update(delta)
        current["version"] = current.get("version", 0) + 1
        await self._redis.set(state_key, json.dumps(current))

    async def delete_state(self, key: str):
        await self.connect()
        await self._redis.delete(f"state:{key}")

    async def list_keys(self, prefix: str = "") -> list[str]:
        await self.connect()
        pattern = f"state:{prefix}*" if prefix else "state:*"
        keys = await self._redis.keys(pattern)
        return [k.replace("state:", "") for k in keys]
