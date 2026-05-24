import json
from collections.abc import Callable
from typing import Optional

import redis.asyncio as redis

from src.core.config import settings


class MessageBus:
    def __init__(self, redis_url: str | None = None):
        self.redis_url = redis_url or settings.REDIS_URL
        self._redis: redis.Redis | None = None
        self._pubsub: Optional = None
        self._handlers: dict[str, list[Callable]] = {}

    async def connect(self):
        if self._redis is None:
            self._redis = await redis.from_url(self.redis_url, decode_responses=True)
            self._pubsub = self._redis.pubsub()

    async def publish(self, channel: str, message: dict):
        await self.connect()
        await self._redis.publish(channel, json.dumps(message))

    def subscribe(self, channel: str, handler: Callable):
        if channel not in self._handlers:
            self._handlers[channel] = []
        self._handlers[channel].append(handler)

    async def listen(self, channels: list[str]):
        await self.connect()
        await self._pubsub.subscribe(*channels)
        async for msg in self._pubsub.listen():
            if msg["type"] != "message":
                continue
            channel = msg["channel"]
            data = json.loads(msg["data"])
            handlers = self._handlers.get(channel, [])
            for handler in handlers:
                await handler(data)

    async def close(self):
        if self._pubsub:
            await self._pubsub.close()
        if self._redis:
            await self._redis.close()
