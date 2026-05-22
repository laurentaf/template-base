import asyncio
import uuid
from datetime import datetime
from typing import Any

from src.agents.base import BaseAgent
from src.schemas.tasks import Task, TaskResult, WorkflowDefinition
from src.schemas.messages import AgentMessage

class OrchestratorAgent(BaseAgent):
    def __init__(self):
        super().__init__("orchestrator", ["orchestration", "workflow_management", "task_decomposition"])

    async def handle_task(self, task: Task) -> TaskResult:
        if task.task_type == "run_workflow":
            return await self._run_workflow(task.payload)
        if task.task_type == "check_health":
            return await self._check_cluster_health()
        return TaskResult(task_id=task.task_id, status="failed", error=f"Unknown type: {task.task_type}")

    async def _run_workflow(self, payload: dict) -> TaskResult:
        workflow = WorkflowDefinition(**payload)
        workflow_id = workflow.workflow_id

        self.log(f"Running workflow: {workflow.name} ({workflow_id})")
        await self.state_manager.set_state(f"workflow:{workflow_id}", {
            "workflow_id": workflow_id, "name": workflow.name,
            "status": "running", "context": workflow.context,
            "task_ids": [t.task_id for t in workflow.tasks],
            "created_at": datetime.now().isoformat()
        })

        # Build dependency graph
        completed = set()
        failed = []
        task_map = {t.task_id: t for t in workflow.tasks}

        while len(completed) < len(workflow.tasks) and not failed:
            for t in workflow.tasks:
                if t.task_id in completed or t.task_id in failed:
                    continue
                # Check dependencies
                deps_met = all(d in completed for d in t.depends_on)
                if deps_met:
                    # Dispatch to appropriate agent type
                    agent_type = t.agent_type
                    await self.enqueue_task(t)
                    self.log(f"Dispatched {t.task_id} -> {agent_type}")

            # Wait for results via message bus
            result_ev = asyncio.Event()
            results = {}

            async def on_completed(data):
                tid = data.get("task_id")
                results[tid] = data.get("result", {})
                result_ev.set()

            self.message_bus.subscribe("events.task.completed", on_completed)
            self.message_bus.subscribe("events.task.failed", lambda d: results.update({d["task_id"]: {"error": d.get("error")}}) or result_ev.set())

            await asyncio.wait_for(result_ev.wait(), timeout=120)
            for tid in list(results.keys()):
                if "error" in results.get(tid, {}):
                    failed.append(tid)
                else:
                    completed.add(tid)

        status = "failed" if failed else "completed"
        await self.state_manager.update_state(f"workflow:{workflow_id}", {
            "status": status, "completed_at": datetime.now().isoformat()
        })
        return TaskResult(task_id=task.task_id, status=status, output={
            "workflow_id": workflow_id,
            "completed": list(completed),
            "failed": failed
        })

    async def _check_cluster_health(self) -> TaskResult:
        agents = await self.registry.discover()
        return TaskResult(task_id="health-check", status="completed", output={
            "agents": agents,
            "total": len(agents)
        })

    async def on_message(self, msg: AgentMessage):
        if msg.topic == "validation.requested":
            self.log(f"Validation requested by {msg.sender}")

async def main():
    agent = OrchestratorAgent()
    await agent.start()
    agent.log("Orchestrator ready. Waiting for tasks...")
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        await agent.stop()

if __name__ == "__main__":
    asyncio.run(main())
