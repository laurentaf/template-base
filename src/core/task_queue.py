import json

import redis.asyncio as redis

STREAM_KEY = "task:queue"
GROUP_NAME = "agents"
CONSUMER_PREFIX = "worker"


class TaskQueue:
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self._redis: redis.Redis | None = None

    async def connect(self):
        if self._redis is None:
            self._redis = await redis.from_url(self.redis_url, decode_responses=True)
            try:
                await self._redis.xgroup_create(STREAM_KEY, GROUP_NAME, id="0", mkstream=True)
            except redis.ResponseError:
                pass

    async def enqueue(self, task_type: str, payload: dict, priority: int = 0) -> str:
        await self.connect()
        entry = json.dumps({"type": task_type, "payload": payload, "priority": priority})
        msg_id = await self._redis.xadd(STREAM_KEY, {"data": entry}, maxlen=10000)
        return msg_id

    async def dequeue(self, consumer_id: str, timeout: int = 5) -> dict | None:
        await self.connect()
        results = await self._redis.xreadgroup(
            GROUP_NAME, consumer_id, {STREAM_KEY: ">"}, count=1, block=timeout * 1000
        )
        if results:
            stream_name, messages = results[0]
            if messages:
                msg_id, fields = messages[0]
                entry = json.loads(fields["data"])
                return {"msg_id": msg_id, **entry}
        return None

    async def acknowledge(self, msg_id: str):
        await self.connect()
        await self._redis.xack(STREAM_KEY, GROUP_NAME, msg_id)

    async def nack(self, msg_id: str):
        await self.connect()
        await self._redis.xack(STREAM_KEY, GROUP_NAME, msg_id)

    async def pending_count(self) -> int:
        await self.connect()
        info = await self._redis.xpending(STREAM_KEY, GROUP_NAME)
        return info.get("pending", 0) if isinstance(info, dict) else 0
