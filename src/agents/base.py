import asyncio
import uuid
from abc import ABC, abstractmethod

from src.core.agent_registry import AgentRegistry
from src.core.auto_doc import auto_doc
from src.core.auto_git import auto_git
from src.core.confidence import ConfidenceReport, confidence_engine
from src.core.config import settings
from src.core.distributed_state import DistributedStateManager
from src.core.learnings import learning_emitter
from src.core.local_backend import (
    LocalAgentRegistry,
    LocalDistributedState,
    LocalMessageBus,
    LocalTaskQueue,
    check_redis,
)
from src.core.message_bus import MessageBus
from src.core.task_queue import CONSUMER_PREFIX, TaskQueue
from src.core.telemetry import setup_observability
from src.schemas.messages import AgentMessage
from src.schemas.tasks import Task, TaskResult


class BaseAgent(ABC):
    def __init__(self, agent_type: str, capabilities: list[str], agent_id: str | None = None):
        self.agent_id = agent_id or f"{agent_type}-{uuid.uuid4().hex[:8]}"
        self.agent_type = agent_type
        self.capabilities = capabilities
        self.running = False
        self._local_mode = False
        self.pre_task_hooks: list = []
        self.post_task_hooks: list = []
        self._last_confidence_report: ConfidenceReport | None = None

        self.state_manager = DistributedStateManager()
        self.task_queue = TaskQueue()
        self.message_bus = MessageBus()
        self.registry = AgentRegistry()

    def register_pre_hook(self, hook):
        self.pre_task_hooks.append(hook)

    def register_post_hook(self, hook):
        self.post_task_hooks.append(hook)

    async def evaluate_confidence(
        self, task_description: str, task_type: str = "",
    ) -> ConfidenceReport:
        report = confidence_engine.evaluate(task_description, task_type)
        self._last_confidence_report = report
        return report

    async def start(self, mode: str = "auto"):
        self.running = True

        try:
            setup_observability(project_name=self.agent_type)
        except Exception:
            pass

        self.post_task_hooks.append(
            lambda t, r, a: auto_doc.update_after_task(t, r, a)
        )
        self.post_task_hooks.append(
            lambda t, r, a: auto_git.auto_commit(t, r, a)
        )
        self.post_task_hooks.append(
            lambda t, r, a: learning_emitter.emit_from_task_result(
                t, r, a, project_name=settings.PROJECT_NAME,
            )
        )

        if mode == "local":
            self._local_mode = True
        elif mode == "auto":
            self._local_mode = not await check_redis()
        else:
            self._local_mode = False

        if self._local_mode:
            self.state_manager = LocalDistributedState()
            self.task_queue = LocalTaskQueue()
            self.message_bus = LocalMessageBus()
            self.registry = LocalAgentRegistry()
            self.log("Local mode — Redis not available")

        await self.state_manager.connect()
        await self.task_queue.connect()
        await self.registry.register(self.agent_id, self.agent_type, self.capabilities)
        await self.registry.set_status(self.agent_id, "idle")

        asyncio.create_task(self._heartbeat_loop())
        asyncio.create_task(self._task_poll_loop())
        asyncio.create_task(self._message_listen_loop())

        await self.on_start()

        self.message_bus.subscribe(f"agent.{self.agent_id}", self._handle_direct_message)
        self.message_bus.subscribe("broadcast.all", self._handle_broadcast)

    async def stop(self):
        self.running = False
        await self.registry.set_status(self.agent_id, "offline")
        await self.on_stop()

    async def _heartbeat_loop(self):
        while self.running:
            await self.registry.heartbeat(self.agent_id)
            await asyncio.sleep(15)

    async def _task_poll_loop(self):
        consumer_id = f"{CONSUMER_PREFIX}-{self.agent_id}"
        while self.running:
            msg = await self.task_queue.dequeue(consumer_id, timeout=3)
            if msg:
                await self.registry.set_status(self.agent_id, "busy")
                task = Task(
                    task_id=msg["msg_id"],
                    task_type=msg["type"],
                    agent_type=self.agent_type,
                    payload=msg["payload"],
                )
            for hook in self.pre_task_hooks:
                try:
                    await hook(task) if asyncio.iscoroutinefunction(hook) else hook(task)
                except Exception:
                    pass
            try:
                result = await self.handle_task(task)
                await self.task_queue.acknowledge(msg["msg_id"])
                await self.message_bus.publish(
                    "events.task.completed",
                    {
                        "task_id": task.task_id,
                        "agent_id": self.agent_id,
                        "result": result.model_dump(),
                    },
                )
                await self._run_post_hooks(
                    task.task_type, result.model_dump(), self.agent_type,
                )
            except Exception as e:
                await self.task_queue.nack(msg["msg_id"])
                await self.message_bus.publish(
                    "events.task.failed",
                    {"task_id": task.task_id, "agent_id": self.agent_id, "error": str(e)},
                )
                await self._run_post_hooks(
                    task.task_type, {"error": str(e)}, self.agent_type,
                )
            finally:
                await self.registry.set_status(self.agent_id, "idle")
            await asyncio.sleep(0.5)

    async def _run_post_hooks(self, task_type, result_dict, agent_type):
        for hook in self.post_task_hooks:
            try:
                if asyncio.iscoroutinefunction(hook):
                    await hook(task_type, result_dict, agent_type)
                else:
                    hook(task_type, result_dict, agent_type)
            except Exception:
                pass

    async def _message_listen_loop(self):
        await self.message_bus.listen(["broadcast.all", f"agent.{self.agent_id}"])

    async def _handle_direct_message(self, data: dict):
        msg = AgentMessage(**data)
        await self.on_message(msg)

    async def _handle_broadcast(self, data: dict):
        msg = AgentMessage(**data)
        if msg.recipient is None or msg.recipient == self.agent_id:
            await self.on_message(msg)

    async def send_message(self, recipient: str, msg: AgentMessage):
        await self.message_bus.publish(f"agent.{recipient}", msg.model_dump())

    async def broadcast(self, msg: AgentMessage):
        await self.message_bus.publish("broadcast.all", msg.model_dump())

    async def enqueue_task(self, task: Task) -> str:
        return await self.task_queue.enqueue(
            task.task_type, task.payload | {"task_id": task.task_id}, task.priority
        )

    async def get_workflow_context(self, workflow_id: str) -> dict:
        state = await self.state_manager.get_state(f"workflow:{workflow_id}")
        return state.get("context", {}) if state else {}

    async def set_workflow_context(self, workflow_id: str, context: dict):
        await self.state_manager.update_state(f"workflow:{workflow_id}", {"context": context})

    # Override points for subclasses
    async def on_start(self):
        pass

    async def on_stop(self):
        pass

    async def on_message(self, msg: AgentMessage):
        pass

    @abstractmethod
    async def handle_task(self, task: Task) -> TaskResult: ...

    def log(self, msg: str):
        print(f"[{self.agent_id}] {msg}")
