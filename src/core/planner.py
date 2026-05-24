"""Project Planner — Confidence-Driven Project Analysis.

On first project interaction:
1. Analyze user's project description
2. Determine required agents, infrastructure, pipelines
3. Research until confidence >= threshold (KB → MCP → internet)
4. Present final plan for user approval (always ask before executing)
5. Create spec/design.md, spec/todo.md, decision log entries
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from src.core.confidence import (
    ConfidenceReport,
    DecisionAction,
    confidence_engine,
)
from src.core.llm import llm


class ProjectPlanner:
    AGENT_SUGGESTIONS: dict[str, list[str]] = {
        "etl": ["data-pipeline"],
        "analytics": ["analytics", "data-pipeline"],
        "ml": ["data-pipeline", "analytics", "code-gen"],
        "rag": ["data-pipeline", "analytics"],
        "real_time": ["data-pipeline", "analytics", "reviewer"],
        "reporting": ["analytics", "code-gen"],
        "full_stack": ["orchestrator", "data-pipeline", "analytics", "code-gen", "reviewer"],
        "data_quality": ["reviewer", "data-pipeline"],
        "code_generation": ["code-gen", "reviewer"],
    }

    INFRA_SUGGESTIONS: dict[str, list[str]] = {
        "etl": ["redis", "postgres", "minio"],
        "analytics": ["redis", "postgres", "duckdb"],
        "ml": ["redis", "postgres", "qdrant", "minio"],
        "rag": ["redis", "postgres", "qdrant"],
        "real_time": ["redis", "postgres", "minio"],
        "reporting": ["redis", "postgres", "duckdb"],
        "full_stack": ["redis", "postgres", "qdrant", "minio", "phoenix"],
        "data_quality": ["redis", "postgres", "duckdb"],
        "code_generation": ["redis"],
    }

    @staticmethod
    async def _kb_lookup(description: str) -> dict[str, Any] | None:
        kb_dir = Path(".opencode/kb")
        if not kb_dir.exists():
            return None
        found = False
        summaries: list[str] = []
        for domain_dir in sorted(kb_dir.iterdir()):
            if not domain_dir.is_dir():
                continue
            index = domain_dir / "index.md"
            if index.exists():
                content = index.read_text(encoding="utf-8").lower()
                desc_words = set(description.lower().split())
                overlap = len(desc_words & set(content.split()))
                if overlap > 2:
                    found = True
                    summaries.append(f"{domain_dir.name}: {overlap} keyword matches")
        if found:
            return {"found": True, "source": "local_kb", "summary": "; ".join(summaries)}
        return None

    @staticmethod
    async def _mcp_query(description: str) -> dict[str, Any] | None:
        try:
            prompt = (
                f"For a data engineering project described as: '{description}'\n"
                "What agents, infrastructure, and data model would you recommend? "
                "Respond with JSON: {\"agents\": [...], \"infrastructure\": [...], "
                "\"data_model\": [...], \"agrees\": true/false}"
            )
            resp = llm.chat([{"role": "user", "content": prompt}], max_tokens=1024)
            try:
                data = json.loads(resp.content)
                return {
                    "found": True,
                    "source": "llm_mcp",
                    "agrees": data.get("agrees", True),
                    "summary": json.dumps(data, indent=2)[:500],
                }
            except json.JSONDecodeError:
                return {
                "found": True,
                "source": "llm_mcp",
                "agrees": True,
                "summary": resp.content[:500],
            }
        except Exception:
            return None

    @staticmethod
    async def _internet_search(description: str) -> dict[str, Any] | None:
        try:
            prompt = (
                f"Research: What is the best data engineering architecture for '{description}'? "
                "Consider: medallion architecture, agent patterns, vector search needs. "
                "Provide specific technology recommendations with production examples."
            )
            resp = llm.chat([{"role": "user", "content": prompt}], max_tokens=1024)
            return {
                "found": True,
                "source": "llm_research",
                "summary": resp.content[:500],
                "production_examples": "production" in resp.content.lower(),
            }
        except Exception:
            return None

    @staticmethod
    async def plan(description: str, research: bool = True):
        print("\n=== Planning Project ===")
        print(f"Description: {description}\n")

        print("Step 1: Classifying project requirements...")
        report: ConfidenceReport
        if research:
            report = await confidence_engine.evaluate_with_research(
                task_description=description,
                task_type="project_planning",
                kb_lookup=ProjectPlanner._kb_lookup,
                mcp_query=ProjectPlanner._mcp_query,
                internet_search=ProjectPlanner._internet_search,
            )
        else:
            report = confidence_engine.evaluate(
                task_description=description,
                task_type="project_planning",
                kb_has_pattern=False,
                mcp_result="silent",
            )

        print("\nStep 2: Confidence Assessment")
        print(f"  Category: {report.category.value}")
        print(f"  Confidence: {report.final_score:.2f} (threshold: {report.threshold:.2f})")
        print(f"  Decision: {report.decision.value}")
        if report.research_rounds > 0:
            print(f"  Research rounds: {report.research_rounds}")
        if report.sources:
            print(f"  Sources: {len(report.sources)}")

        print("\nStep 3: Generating plan...")
        plan_data = await ProjectPlanner._generate_plan(description, report)

        print("\nStep 4: Presenting plan for approval...")
        ProjectPlanner._print_plan(plan_data)

        if report.decision == DecisionAction.ASK_USER or report.decision == DecisionAction.REFUSE:
            print("\nConfidence below threshold — your approval is required.")

        proceed = input("\nProceed with this plan? [Y/n]: ").strip().lower()
        if proceed in ("n", "no"):
            print("Plan cancelled. Adjust description and try again.")
            return

        await ProjectPlanner._save_plan(plan_data, description)
        print("\nPlan saved. Start agents with: ltade agents start")

    @staticmethod
    async def _generate_plan(description: str, report: ConfidenceReport) -> dict[str, Any]:
        desc_lower = description.lower()
        domain = "full_stack"
        for key in ProjectPlanner.AGENT_SUGGESTIONS:
            syns = [key.replace("_", " "), key.replace("-", " ")]
            if key in desc_lower or any(syn in desc_lower for syn in syns):
                domain = key
                break

        agents = ProjectPlanner.AGENT_SUGGESTIONS.get(domain, ["orchestrator", "data-pipeline"])
        infrastructure = ProjectPlanner.INFRA_SUGGESTIONS.get(domain, ["redis", "postgres"])

        prompt = (
            f"Project: {description}\n\n"
            "Design a data model with 3-5 entities. For each entity, provide:\n"
            "- entity name\n- store (postgres/qdrant/duckdb)\n- fields with types\n\n"
            "Also suggest:\n"
            f"- Medallion layers needed (bronze/silver/gold)\n"
            "- Key quality rules\n"
            "- Initial pipeline steps\n\n"
            "Respond as JSON with keys: entities, medallion_layers, quality_rules, pipeline_steps"
        )
        try:
            resp = llm.chat([{"role": "user", "content": prompt}], max_tokens=2048)
            ai_plan = json.loads(resp.content)
        except Exception:
            ai_plan = {
                "entities": [],
                "medallion_layers": ["bronze", "silver", "gold"],
                "quality_rules": [],
                "pipeline_steps": [],
            }

        return {
            "description": description,
            "domain": domain,
            "agents": agents,
            "infrastructure": infrastructure,
            "confidence": report.final_score,
            "ai_plan": ai_plan,
            "research_sources": [s.model_dump() for s in report.sources],
        }

    @staticmethod
    def _print_plan(plan_data: dict[str, Any]):
        print("\n" + "=" * 60)
        print("PROJECT PLAN")
        print("=" * 60)
        print(f"\nDomain: {plan_data['domain']}")
        print(f"Confidence: {plan_data['confidence']:.2f}")
        print(f"\nRequired Agents: {', '.join(plan_data['agents'])}")
        print(f"Infrastructure: {', '.join(plan_data['infrastructure'])}")

        ai_plan = plan_data.get("ai_plan", {})
        if ai_plan.get("entities"):
            print(f"\nData Model ({len(ai_plan['entities'])} entities):")
            for entity in ai_plan["entities"]:
                if isinstance(entity, dict):
                    print(f"  - {entity.get('name', entity)}: {entity.get('store', 'postgres')}")

        if ai_plan.get("medallion_layers"):
            print(f"\nMedallion Layers: {' → '.join(ai_plan['medallion_layers'])}")

        if ai_plan.get("pipeline_steps"):
            print("\nPipeline Steps:")
            for i, step in enumerate(ai_plan["pipeline_steps"][:5], 1):
                print(f"  {i}. {step}")

        if ai_plan.get("quality_rules"):
            print(f"\nQuality Rules: {', '.join(str(r) for r in ai_plan['quality_rules'][:5])}")

    @staticmethod
    async def _save_plan(plan_data: dict[str, Any], description: str):
        root = Path.cwd()

        design_path = root / "spec" / "design.md"
        design_content = "# Architecture Design\n\n"
        design_content += f"**Created:** {datetime.now().isoformat()[:10]}\n"
        design_content += f"**Description:** {description}\n"
        design_content += f"**Domain:** {plan_data['domain']}\n"
        design_content += f"**Confidence:** {plan_data['confidence']:.2f}\n\n"
        design_content += "## Agents\n\n"
        for agent in plan_data["agents"]:
            design_content += f"- {agent}\n"
        design_content += "\n## Infrastructure\n\n"
        for infra in plan_data["infrastructure"]:
            design_content += f"- {infra}\n"

        ai_plan = plan_data.get("ai_plan", {})
        if ai_plan.get("entities"):
            design_content += (
                "\n## Data Model\n\n"
                "| Entity | Store | Fields |\n"
                "|--------|-------|--------|\n"
            )
            for entity in ai_plan["entities"]:
                if isinstance(entity, dict):
                    name = entity.get("name", "unknown")
                    store = entity.get("store", "postgres")
                    fields = ", ".join(str(f) for f in entity.get("fields", []))
                    design_content += f"| {name} | {store} | {fields} |\n"

        if ai_plan.get("medallion_layers"):
            layers = " → ".join(ai_plan["medallion_layers"])
            design_content += f"\n## Medallion Layers\n\n{layers}\n"

        if ai_plan.get("pipeline_steps"):
            design_content += "\n## Pipeline Steps\n\n"
            for i, step in enumerate(ai_plan["pipeline_steps"], 1):
                design_content += f"{i}. {step}\n"

        if plan_data.get("research_sources"):
            design_content += "\n## Research Sources\n\n"
            for src in plan_data["research_sources"]:
                src_type = src.get("source_type", "unknown")
            src_name = src.get("name", "")
            src_result = src.get("result", "")
            design_content += f"- {src_type}: {src_name} — {src_result}\n"

        design_path.write_text(design_content, encoding="utf-8")

        todo_path = root / "spec" / "todo.md"
        todo_content = f"# Active Tasks\n\n**Created:** {datetime.now().isoformat()[:10]}\n\n"
        todo_content += "## Phase 1: Infrastructure\n\n"
        for infra in plan_data["infrastructure"]:
            todo_content += f"- [ ] Set up {infra}\n"
        todo_content += "\n## Phase 2: Data Model\n\n"
        for entity in ai_plan.get("entities", []):
            if isinstance(entity, dict):
                todo_content += f"- [ ] Create {entity.get('name', 'entity')} table\n"
        todo_content += "\n## Phase 3: Pipelines\n\n"
        for step in ai_plan.get("pipeline_steps", []):
            todo_content += f"- [ ] {step}\n"
        todo_content += "\n## Phase 4: Quality\n\n"
        for rule in ai_plan.get("quality_rules", []):
            todo_content += f"- [ ] Implement quality rule: {rule}\n"
        todo_content += "\n## Phase 5: Agents\n\n"
        for agent in plan_data["agents"]:
            todo_content += f"- [ ] Verify {agent} agent\n"
        todo_path.write_text(todo_content, encoding="utf-8")

        print("  Written: spec/design.md")
        print("  Written: spec/todo.md")
