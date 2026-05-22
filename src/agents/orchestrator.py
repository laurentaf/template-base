import asyncio
import json
import uuid
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from src.agents.base import BaseAgent
from src.core.llm import llm
from src.schemas.messages import AgentMessage
from src.schemas.tasks import Task, TaskResult


class WorkflowState(TypedDict):
    workflow_id: str
    name: str
    description: str
    context: dict
    tasks: list[dict]
    completed: list[str]
    failed: list[str]
    results: dict[str, Any]
    status: str


class OrchestratorAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            "orchestrator", ["orchestration", "workflow_management", "task_decomposition"]
        )
        self.graph = self._build_graph()

    def _build_graph(self):
        g = StateGraph(WorkflowState)

        async def decompose(state: WorkflowState) -> dict:
            prompt = (
                f"Workflow: {state['name']}\n"
                f"Description: {state['description']}\n"
                f"Context: {json.dumps(state['context'])}\n\n"
                "Decompose this work into sequential steps. Return a JSON array of "
                'objects with keys: "step_id", "description", "agent_type" (one of: '
                "data-pipeline, analytics, code-gen, reviewer)."
            )
            resp = llm.chat([{"role": "user", "content": prompt}])
            try:
                data = json.loads(resp.content)
                steps = data if isinstance(data, list) else data.get("steps", [])
                return {"tasks": steps}
            except json.JSONDecodeError:
                return {"tasks": []}

        async def dispatch(state: WorkflowState) -> dict:
            for t in state.get("tasks", []):
                sid = t.get("step_id")
                if sid in state["completed"] or sid in state["failed"]:
                    continue
                deps = t.get("depends_on", [])
                if all(d in state["completed"] for d in deps):
                    task = Task(
                        task_id=sid or str(uuid.uuid4()),
                        task_type=t.get("task_type", "run_query"),
                        agent_type=t.get("agent_type", "data-pipeline"),
                        payload={
                            "query": t.get("query", ""),
                            "description": t.get("description", ""),
                            "workflow_id": state["workflow_id"],
                        },
                    )
                    await self.enqueue_task(task)
            return {}

        async def collect(state: WorkflowState) -> dict:
            new_completed = list(state["completed"])
            new_failed = list(state["failed"])
            for t in state.get("tasks", []):
                sid = t.get("step_id")
                if sid in new_completed or sid in new_failed:
                    continue
                deps = t.get("depends_on", [])
                if not all(d in new_completed for d in deps):
                    continue
                result_key = f"task:{sid}"
                result_state = await self.state_manager.get_state(result_key)
                if result_state:
                    if result_state.get("status") == "completed":
                        new_completed.append(sid)
                    elif result_state.get("status") == "failed":
                        new_failed.append(sid)
            return {"completed": new_completed, "failed": new_failed}

        async def finalize(state: WorkflowState) -> dict:
            status = "failed" if state["failed"] else "completed"
            return {"status": status}

        def should_continue(state: WorkflowState) -> str:
            pending = [
                t
                for t in state.get("tasks", [])
                if t["step_id"] not in state["completed"] and t["step_id"] not in state["failed"]
            ]
            return "finalize" if not pending else "collect"

        g.add_node("decompose", decompose)
        g.add_node("dispatch", dispatch)
        g.add_node("collect", collect)
        g.add_node("finalize", finalize)

        g.add_edge(START, "decompose")
        g.add_edge("decompose", "dispatch")
        g.add_conditional_edges(
            "dispatch",
            should_continue,
            {
                "collect": "collect",
                "finalize": "finalize",
            },
        )
        g.add_edge("collect", "dispatch")
        g.add_edge("finalize", END)

        return g.compile(checkpointer=MemorySaver())

    async def handle_task(self, task: Task) -> TaskResult:
        if task.task_type == "run_workflow":
            return await self._run_workflow(task)
        if task.task_type == "check_health":
            return await self._check_cluster_health()
        if task.task_type == "llm_chat":
            return await self._llm_chat(task)
        return TaskResult(task_id=task.task_id, status="failed", error=f"Unknown: {task.task_type}")

    async def _run_workflow(self, task: Task) -> TaskResult:
        workflow_id = task.payload.get("workflow_id", str(uuid.uuid4()))
        initial: WorkflowState = {
            "workflow_id": workflow_id,
            "name": task.payload.get("name", "unnamed"),
            "description": task.payload.get("description", ""),
            "context": task.payload.get("context", {}),
            "tasks": [],
            "completed": [],
            "failed": [],
            "results": {},
            "status": "pending",
        }
        await self.state_manager.set_state(f"workflow:{workflow_id}", {"status": "running"})
        config = {"configurable": {"thread_id": workflow_id}}
        final_state = await self.graph.ainvoke(initial, config)
        await self.state_manager.update_state(
            f"workflow:{workflow_id}",
            {
                "status": final_state["status"],
                "completed": final_state["completed"],
                "failed": final_state["failed"],
            },
        )
        return TaskResult(
            task_id=task.task_id,
            status="completed",
            output={
                "workflow_id": workflow_id,
                "completed": final_state["completed"],
                "failed": final_state["failed"],
            },
        )

    async def _check_cluster_health(self) -> TaskResult:
        agents = await self.registry.discover()
        health = llm.chat(
            [
                {
                    "role": "user",
                    "content": f"Summarize this cluster state: {json.dumps(agents, indent=2)}",
                }
            ]
        )
        return TaskResult(
            task_id="health-check",
            status="completed",
            output={
                "agents": agents,
                "total": len(agents),
                "summary": health.content,
            },
        )

    async def _llm_chat(self, task: Task) -> TaskResult:
        messages = task.payload.get("messages", [])
        resp = llm.chat(messages)
        return TaskResult(
            task_id=task.task_id,
            status="completed",
            output={
                "content": resp.content,
                "model": resp.model,
                "tokens": resp.input_tokens + resp.output_tokens,
                "latency_ms": resp.latency_ms,
            },
        )

    async def on_message(self, msg: AgentMessage):
        if msg.topic == "validation.requested":
            self.log(f"Validation requested by {msg.sender}")

    async def on_start(self):
        self.log("Orchestrator ready with LangGraph workflow engine")

    async def on_stop(self):
        self.log("Orchestrator stopping")


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
