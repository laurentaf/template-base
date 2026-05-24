"""Consensus Engine — Multi-Agent Workflow Patterns.

Implements 4 collaboration patterns:
- CONSENSUS: Multiple agents vote; majority wins with quorum
- PARALLEL: Fan-out to N agents, gather all results
- HIERARCHICAL: Orchestrator delegates to sub-orchestrators
- SEQUENTIAL: Chain of agents, each building on previous output

Informed by CrewAI processes (sequential, hierarchical) and
multi-crew coordination patterns (triage-investigation-report).
"""

import asyncio
import uuid
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from src.schemas.tasks import Task, TaskResult


class WorkflowPattern(StrEnum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    HIERARCHICAL = "hierarchical"
    CONSENSUS = "consensus"


class Vote(BaseModel):
    agent_id: str
    agent_type: str
    vote_value: Any
    confidence: float
    reasoning: str = ""


class ConsensusResult(BaseModel):
    pattern: WorkflowPattern
    votes: list[Vote] = Field(default_factory=list)
    majority_value: Any = None
    agreement_ratio: float = 0.0
    quorum_met: bool = False
    final_result: Any = None
    confidence: float = 0.0
    requires_user_approval: bool = False
    reasoning: str = ""


class ConsensusEngine:
    DEFAULT_QUORUM = 0.6
    MIN_VOTERS = 2

    def select_pattern(
        self,
        task_type: str,
        task_description: str = "",
        available_agents: list[dict] | None = None,
    ) -> WorkflowPattern:
        text = f"{task_type} {task_description}".lower()

        consensus_keywords = [
            "architecture_decision", "design_choice", "technology_selection",
            "trade_off", "evaluate", "recommend", "opinion",
        ]
        parallel_keywords = [
            "validate_all", "check_all", "audit_all", "review_all",
            "batch", "fan_out", "scatter", "independent",
        ]
        hierarchical_keywords = [
            "complex_workflow", "multi_phase", "sub_orchestrate",
            "delegate", "escalate", "tiered",
        ]

        for kw in consensus_keywords:
            if kw in text:
                return WorkflowPattern.CONSENSUS
        for kw in parallel_keywords:
            if kw in text:
                return WorkflowPattern.PARALLEL
        for kw in hierarchical_keywords:
            if kw in text:
                return WorkflowPattern.HIERARCHICAL
        return WorkflowPattern.SEQUENTIAL

    async def run_consensus(
        self,
        task: Task,
        agent_handlers: dict[str, Any],
        quorum: float | None = None,
        confidence_threshold: float = 0.95,
    ) -> ConsensusResult:
        quorum = quorum or self.DEFAULT_QUORUM
        votes: list[Vote] = []
        agent_ids = list(agent_handlers.keys())

        if len(agent_ids) < self.MIN_VOTERS:
            return ConsensusResult(
                pattern=WorkflowPattern.CONSENSUS,
                votes=[],
                quorum_met=False,
                requires_user_approval=True,
                reasoning=f"Not enough voters ({len(agent_ids)} < {self.MIN_VOTERS})",
            )

        tasks = {}
        for aid, handler in agent_handlers.items():
            tasks[aid] = handler(task)
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)

        for aid, result in zip(agent_ids, results):
            if isinstance(result, Exception):
                continue
            vote_value = result.output if result.status == "completed" else None
            confidence = result.metrics.get("confidence", 0.5) if result.metrics else 0.5
            votes.append(Vote(
                agent_id=aid,
                agent_type=aid.split("-")[0] if "-" in aid else aid,
                vote_value=vote_value,
                confidence=confidence,
                reasoning=result.metrics.get("reasoning", "") if result.metrics else "",
            ))

        if not votes:
            return ConsensusResult(
                pattern=WorkflowPattern.CONSENSUS,
                votes=[],
                quorum_met=False,
                requires_user_approval=True,
                reasoning="All voters failed",
            )

        vote_values: dict[str, int] = {}
        for v in votes:
            key = str(v.vote_value)
            vote_values[key] = vote_values.get(key, 0) + 1

        majority_key = max(vote_values, key=vote_values.get)
        majority_count = vote_values[majority_key]
        agreement_ratio = majority_count / len(votes)
        quorum_met = agreement_ratio >= quorum

        confident_votes = [v for v in votes if v.vote_value is not None]
        avg_confidence = sum(v.confidence for v in confident_votes) / max(1, len(confident_votes))

        requires_approval = not quorum_met or avg_confidence < confidence_threshold

        return ConsensusResult(
            pattern=WorkflowPattern.CONSENSUS,
            votes=votes,
            majority_value=majority_key if quorum_met else None,
            agreement_ratio=round(agreement_ratio, 3),
            quorum_met=quorum_met,
            final_result=majority_key if quorum_met else None,
            confidence=round(avg_confidence, 4),
            requires_user_approval=requires_approval,
            reasoning=(
            f"Agreement: {agreement_ratio:.0%} (quorum: {quorum:.0%}),"
            f" avg confidence: {avg_confidence:.2f}"
        ),
        )

    async def run_parallel(
        self,
        task: Task,
        agent_handlers: dict[str, Any],
        gather_all: bool = True,
        top_k: int | None = None,
    ) -> ConsensusResult:
        tasks = {}
        for aid, handler in agent_handlers.items():
            tasks[aid] = handler(task)
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)

        successful: list[dict] = []
        for aid, result in zip(agent_handlers.keys(), results):
            if isinstance(result, Exception):
                continue
            if result.status == "completed":
                successful.append({
                    "agent_id": aid,
                    "output": result.output,
                    "metrics": result.metrics,
                })

        if top_k and len(successful) > top_k:
            successful.sort(key=lambda x: x.get("metrics", {}).get("confidence", 0), reverse=True)
            successful = successful[:top_k]

        return ConsensusResult(
            pattern=WorkflowPattern.PARALLEL,
            final_result=successful if gather_all else (successful[0] if successful else None),
            confidence=max(
                (r.get("metrics", {}).get("confidence", 0) for r in successful), default=0
            ),
            requires_user_approval=False,
            reasoning=f"Parallel execution: {len(successful)}/{len(agent_handlers)} succeeded",
        )

    async def run_sequential(
        self,
        tasks_chain: list[tuple[Task, Any]],
    ) -> ConsensusResult:
        results: list[dict] = []
        context: dict[str, Any] = {}

        for task, handler in tasks_chain:
            task.payload = {**task.payload, **context}
            try:
                result = await handler(task)
                if result.status == "completed":
                    results.append({"task_id": task.task_id, "output": result.output})
                    if isinstance(result.output, dict):
                        context.update(result.output)
                else:
                    results.append({"task_id": task.task_id, "error": result.error})
            except Exception as e:
                results.append({"task_id": task.task_id, "error": str(e)})

        last_output = results[-1].get("output") if results else None

        return ConsensusResult(
            pattern=WorkflowPattern.SEQUENTIAL,
            final_result=last_output,
            confidence=0.9 if all("error" not in r for r in results) else 0.3,
            requires_user_approval=False,
            reasoning=(
            f"Sequential chain: {len(results)} steps,"
            f" {sum(1 for r in results if 'error' not in r)} succeeded"
        ),
        )

    async def run_hierarchical(
        self,
        task: Task,
        manager_handler: Any,
        worker_handlers: dict[str, Any],
        max_delegation_rounds: int = 3,
    ) -> ConsensusResult:
        delegation_plan = await manager_handler(task)
        if isinstance(delegation_plan, TaskResult):
            delegation_plan = delegation_plan.output or {}

        sub_tasks = delegation_plan.get("sub_tasks", [])
        if not sub_tasks:
            return ConsensusResult(
                pattern=WorkflowPattern.HIERARCHICAL,
                final_result=delegation_plan,
                confidence=0.7,
                requires_user_approval=True,
                reasoning="Manager produced no sub-tasks",
            )

        worker_results: list[dict] = []
        for round_num in range(max_delegation_rounds):
            pending = [
            st for st in sub_tasks
            if st.get("step_id") not in {r["step_id"] for r in worker_results}
        ]
            if not pending:
                break

            for sub_task_def in pending:
                agent_type = sub_task_def.get("agent_type", "data-pipeline")
                handler = worker_handlers.get(agent_type)
                if not handler:
                    worker_results.append({
                "step_id": sub_task_def.get("step_id"),
                "error": f"No handler for {agent_type}",
            })
                    continue

                sub_task = Task(
                    task_id=sub_task_def.get("step_id", str(uuid.uuid4())),
                    task_type=sub_task_def.get("task_type", "run_query"),
                    agent_type=agent_type,
                    payload=sub_task_def.get("payload", {}),
                )
                try:
                    result = await handler(sub_task)
                    worker_results.append({
                        "step_id": sub_task_def.get("step_id"),
                        "status": result.status,
                        "output": result.output,
                    })
                except Exception as e:
                    worker_results.append({
                        "step_id": sub_task_def.get("step_id"),
                        "error": str(e),
                    })

        synthesis_task = Task(
            task_id=f"synthesize-{task.task_id}",
            task_type="synthesize",
            agent_type="orchestrator",
            payload={"worker_results": worker_results, "original_task": task.payload},
        )
        final = await manager_handler(synthesis_task)
        final_output = final.output if isinstance(final, TaskResult) else final

        return ConsensusResult(
            pattern=WorkflowPattern.HIERARCHICAL,
            final_result=final_output,
            confidence=0.85,
            requires_user_approval=True,
            reasoning=(
            f"Hierarchical: {len(worker_results)} sub-tasks"
            f" across {max_delegation_rounds} rounds"
        ),
        )


consensus_engine = ConsensusEngine()
