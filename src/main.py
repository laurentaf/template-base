from pathlib import Path

import typer

app = typer.Typer(help="LTADE — Laurent Template AI Data Engineering")

decision_app = typer.Typer(help="Record, log, and manage architecture decisions.")
rag_app = typer.Typer(help="Ingest documents and search with RAG (DuckDB VSS).")
agents_app = typer.Typer(help="Manage agent lifecycle (start/stop/status).")
evolve_app = typer.Typer(help="Self-evolve: harvest learnings, improve template across projects.")

app.add_typer(decision_app, name="decision")
app.add_typer(rag_app, name="rag")
app.add_typer(agents_app, name="agents")
app.add_typer(evolve_app, name="evolve")


def _ensure_observability():
    try:
        from src.core.telemetry import setup_observability

        setup_observability("ltade")
    except Exception:
        pass


@app.command()
def generate_data():
    """Generate synthetic e-commerce data."""
    from data.generators.ecommerce import generate_all

    result = generate_all()
    typer.echo(f"Generated: {result}")


@app.command()
def pipeline():
    """Run the Medallion pipeline (Bronze → Silver → Gold)."""
    from src.pipelines.medallion.run import run_medallion

    run_medallion()


@app.command()
def flowcheck():
    """Check pipeline status."""
    from cli.flowcheck import cmd_status

    cmd_status(None)


@app.command()
def describe(table: str):
    """Describe a dataset via AI."""
    import asyncio

    from src.agents.analytics_agent import AnalyticsAgent
    from src.schemas.tasks import Task

    async def run():
        agent = AnalyticsAgent()
        await agent.start()
        result = await agent.handle_task(
            Task(
                task_id="describe",
                task_type="describe_dataset",
                agent_type="analytics",
                payload={
                    "table": table,
                    "db_path": "data/silver.duckdb",
                    "layer": "silver",
                },
            )
        )
        await agent.stop()
        if result.status == "completed":
            typer.echo(f"\nDataset: {result.output['table']}")
            typer.echo(f"Rows: {result.output['rows']}")
            for col in result.output.get("columns", []):
                c, t = col["column"], col["type"]
                n, d = col["nulls"], col["distinct"]
                typer.echo(f" {c:25s} {t:15s} nulls:{n:>5d} distinct:{d}")
            typer.echo(f"\nAI Description:\n{result.output.get('description', 'N/A')}")
        else:
            typer.echo(f"Error: {result.error}")

    asyncio.run(run())


@app.command()
def quality(table: str):
    """Run quality checks on a table."""
    from src.core.data_quality import DataQualityValidator, QualityCheck

    validator = DataQualityValidator("data/silver.duckdb")
    checks = [
        QualityCheck(column="id", rule="not_null"),
        QualityCheck(column="id", rule="unique"),
    ]
    results = validator.check_table(f"silver.{table}", checks)
    typer.echo(validator.report(results))
    validator.close()


# ── Decision subcommands ───────────────────────────────────


@decision_app.command("add")
def decision_add(
    title: str = typer.Option(..., "--title", "-t", help="Decision title"),
    context: str = typer.Option(..., "--context", "-c", help="Why this decision was needed"),
    decision: str = typer.Option(..., "--decision", "-d", help="What was decided"),
    consequences: str = typer.Option(
        ..., "--consequences", "-q", help="Impact of the decision"
    ),
    phase: str = typer.Option("design", "--phase", "-p", help="SDD phase"),
    author: str = typer.Option("user", "--author", "-a", help="Who made the decision"),
    feature: str = typer.Option(None, "--feature", "-f", help="Feature name"),
):
    """Record a new architecture decision."""
    from src.core.decision_log import DecisionLogStore
    from src.schemas.decisions import DecisionLog

    store = DecisionLogStore()
    entry = DecisionLog(
        id=store.next_id(),
        title=title,
        status="accepted",
        context=context,
        decision=decision,
        consequences=consequences,
        sdd_phase=phase,
        author=author,
        feature=feature,
    )
    store.add(entry)
    typer.echo(f"Recorded {entry.id}: {entry.title}")


@decision_app.command("log")
def decision_log(
    phase: str = typer.Option(None, "--phase", "-p", help="Filter by SDD phase"),
    status: str = typer.Option(None, "--status", "-s", help="Filter by status"),
    feature: str = typer.Option(None, "--feature", "-f", help="Filter by feature"),
):
    """List all architecture decisions."""
    from src.core.decision_log import DecisionLogStore
    from src.schemas.decisions import DecisionStatus

    store = DecisionLogStore()
    entries = store.all()
    if phase:
        entries = store.by_phase(phase)
    if status:
        entries = store.by_status(DecisionStatus(status))
    if feature:
        entries = store.by_feature(feature)

    if not entries:
        typer.echo("No decisions recorded yet.")
        return
    for e in entries:
        typer.echo(f"[{e.id}] {e.title} ({e.status}) — {e.sdd_phase} — {e.date[:10]}")
        typer.echo(f" {e.decision[:80]}...")


@decision_app.command("status")
def decision_status():
    """Show decision log summary."""
    from src.core.decision_log import DecisionLogStore

    store = DecisionLogStore()
    summary = store.status_summary()
    typer.echo(f"Decisions: {summary['total']} total")
    typer.echo(f" Proposed: {summary['proposed']}")
    typer.echo(f" Accepted: {summary['accepted']}")
    typer.echo(f" Deprecated: {summary['deprecated']}")
    typer.echo(f" Superseded: {summary['superseded']}")
    typer.echo(f" File: {summary['file']}")


# ── RAG subcommands ────────────────────────────────────────


@rag_app.command("ingest")
def rag_ingest(
    directory: str = typer.Argument(".", help="Directory to ingest"),
    db: str = typer.Option("data/rag.duckdb", "--db", help="Output DuckDB path"),
):
    """Ingest documents into the RAG vector store."""
    from src.rag.ingest import ingest_directory

    result = ingest_directory(directory, db_path=db)
    typer.echo(
        f"Ingested {result['chunks']} chunks from {result['files']} files into {result['db']}"
    )


@rag_app.command("search")
def rag_search(
    query: str = typer.Argument(..., help="Search query"),
    db: str = typer.Option("data/rag.duckdb", "--db", help="DuckDB path"),
    top_k: int = typer.Option(5, "--top-k", "-k", help="Number of results"),
):
    """Search the vector store."""
    from src.rag.retrieve import search as rag_search_fn

    results = rag_search_fn(query, db_path=db, top_k=top_k)
    if not results:
        typer.echo("No results found.")
        return
    for r in results:
        typer.echo(f"[{r['score']:.3f}] {r['source']}")
        typer.echo(f" {r['content'][:120]}...")


# ── Top-level commands ─────────────────────────────────────


@app.command()
def sync(
    project: str = typer.Argument(".", help="Project directory to sync"),
    template: str = typer.Option(
        "E:\\projects\\template-base", "--template", "-t", help="Template directory"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", "-n", help="Show what would change without applying"
    ),
):
    """Sync project with latest template changes."""
    from src.core.template_sync import sync_project

    result = sync_project(
        str(Path(project).resolve()), str(Path(template).resolve()), dry_run=dry_run
    )

    if not result["success"]:
        typer.echo(f"Error: {result['error']}")
        raise typer.Exit(1)

    typer.echo(
        f"Template sync: {result['unchanged']} unchanged, {len(result['updated'])} updated"
    )
    if result["updated"]:
        for f in result["updated"]:
            typer.echo(f" Updated: {f}")
    if result["new"]:
        typer.echo(f" New files ({len(result['new'])}):")
        for f in result["new"]:
            typer.echo(f" + {f}")
    if result["conflicts"]:
        typer.echo(f" Conflicts ({len(result['conflicts'])}):")
        for f in result["conflicts"]:
            typer.echo(f" ! {f}")
    if result["removed"]:
        typer.echo(f" Removed from template ({len(result['removed'])}):")
        for f in result["removed"]:
            typer.echo(f" - {f}")


@app.command()
def init(
    project_name: str = typer.Option(None, "--name", "-n", help="Project name"),
    tier: str = typer.Option("development", "--tier", "-t", help="Execution tier"),
    skip_infra: bool = typer.Option(
        False, "--skip-infra", help="Skip infrastructure checks"
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Accept defaults without prompts"),
):
    """Initialize project on first run (bootstrap)."""
    import asyncio

    from src.core.bootstrapper import BootstrapEngine

    engine = BootstrapEngine(
        project_name=project_name, tier=tier, skip_infra=skip_infra, yes=yes
    )
    asyncio.run(engine.run())


@app.command()
def health():
    """Check health of all project services."""
    import asyncio

    from src.core.bootstrapper import HealthChecker

    asyncio.run(HealthChecker.run_and_print())


@app.command()
def plan(
    description: str = typer.Argument(..., help="Describe what this project does"),
    research: bool = typer.Option(
        True, "--research/--no-research", help="Research before planning"
    ),
):
    """Analyze project requirements and create execution plan."""
    import asyncio

    from src.core.planner import ProjectPlanner

    asyncio.run(ProjectPlanner.plan(description, research=research))


@app.command()
def template_info(
    project: str = typer.Option(".", "--project", "-p", help="Project directory"),
    template: str = typer.Option(
        "E:\\projects\\template-base", "--template", "-t", help="Template directory"
    ),
):
    """Write .template-info.json for a project (used by ltade-new)."""
    from src.core.template_sync import get_git_commit, save_template_info, scan_template

    files = scan_template(template)
    commit = get_git_commit(template)
    save_template_info(str(Path(project).resolve()), template, commit, files)
    typer.echo(f"Written .template-info.json ({len(files)} files tracked)")


# ── Agents subcommands ─────────────────────────────────────


@agents_app.command("start")
def agents_start(
    agent_types: str = typer.Option(
        "all", "--types", "-t", help="Comma-separated agent types or 'all'"
    ),
    mode: str = typer.Option(
        "auto", "--mode", "-m", help="auto, local, or distributed"
    ),
):
    """Start agent workers."""
    import asyncio

    from src.core.bootstrapper import AgentManager

    asyncio.run(AgentManager.start_agents(agent_types, mode))


@agents_app.command("stop")
def agents_stop():
    """Stop all running agent workers."""
    import asyncio

    from src.core.bootstrapper import AgentManager

    asyncio.run(AgentManager.stop_agents())


@agents_app.command("status")
def agents_status():
    """Show status of all registered agents."""
    import asyncio

    from src.core.bootstrapper import AgentManager

    asyncio.run(AgentManager.show_status())


# ── Evolve subcommands ─────────────────────────────────────


@evolve_app.command("discover")
def evolve_discover():
    """Discover projects with .learnings/ and register them."""
    from src.core.evolve_engine import evolve_engine

    projects = evolve_engine.discover_projects()
    typer.echo(f"\nDiscovered {len(projects)} projects:")
    for p in projects:
        typer.echo(f" {p.name}: {p.path} ({p.status}, {p.learning_count} learnings)")


@evolve_app.command("register")
def evolve_register(
    path: str = typer.Argument(".", help="Project directory to register"),
    name: str = typer.Option("", "--name", "-n", help="Project name override"),
):
    """Register a project for evolve harvesting."""
    from src.core.evolve_engine import evolve_engine

    entry = evolve_engine.register_project(path, name=name)
    typer.echo(f"Registered: {entry.name} at {entry.path}")


@evolve_app.command("harvest")
def evolve_harvest(
    project: str = typer.Option(
        "", "--project", "-p", help="Specific project path (empty = all)"
    ),
):
    """Harvest learnings from projects."""
    from src.core.evolve_engine import evolve_engine

    if project:
        learnings = evolve_engine.harvest(project)
        typer.echo(f"Harvested {len(learnings)} learnings from {project}")
        for learning in learnings:
            typer.echo(f" [{learning.category.value}] {learning.title}")
    else:
        results = evolve_engine.harvest_all()
        total = sum(len(v) for v in results.values())
        typer.echo(f"\nHarvested {total} learnings from {len(results)} projects:")
        for name, items in results.items():
            typer.echo(f" {name}: {len(items)} learnings")


@evolve_app.command("status")
def evolve_status():
    """Show evolve engine status."""
    from src.core.evolve_engine import evolve_engine

    evolve_engine.print_status()


@evolve_app.command("analyze")
def evolve_analyze():
    """Analyze harvested learnings and show high-value items."""
    from src.core.evolve_engine import evolve_engine

    analysis = evolve_engine.analyze()
    typer.echo("\n=== Evolve Analysis ===\n")
    typer.echo(f"Total learnings: {analysis['total']}")
    typer.echo(f"High-value items: {analysis['high_value']}")
    typer.echo("\nBy Category:")
    for cat, count in analysis["by_category"].items():
        typer.echo(f" {cat}: {count}")
    typer.echo("\nBy Domain:")
    for domain, count in analysis["by_domain"].items():
        typer.echo(f" {domain}: {count}")
    if analysis["high_value_items"]:
        typer.echo("\nTop High-Value:")
        for item in analysis["high_value_items"]:
            typer.echo(f" [{item['id']}] {item['title']} ({item['category']})")


@evolve_app.command("apply")
def evolve_apply(
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Show what would change"),
    template: str = typer.Option(
        "E:\\projects\\template-base", "--template", "-t", help="Template path"
    ),
):
    """Apply harvested learnings to the template."""
    from src.core.evolve_engine import EvolveEngine

    engine = EvolveEngine(template_path=template)
    changes = engine.apply(dry_run=dry_run)
    if not changes:
        typer.echo("No improvements to apply.")
        return
    action = "Would apply" if dry_run else "Applied"
    typer.echo(f"\n{action} {len(changes)} improvements:")
    for c in changes:
        typer.echo(f" [{c.category}] {c.title} → {c.target_file}")


@evolve_app.command("rollback")
def evolve_rollback(
    change_id: str = typer.Option("", "--id", help="Specific change ID (empty = last)"),
    template: str = typer.Option(
        "E:\\projects\\template-base", "--template", "-t", help="Template path"
    ),
):
    """Rollback an applied evolve change."""
    from src.core.evolve_engine import EvolveEngine

    engine = EvolveEngine(template_path=template)
    restored = engine.rollback(change_id or None)
    if restored:
        typer.echo(f"Rolled back: {', '.join(restored)}")
    else:
        typer.echo("Nothing to rollback.")


@evolve_app.command("daemon")
def evolve_daemon(
    interval: int = typer.Option(
        300, "--interval", "-i", help="Seconds between harvest cycles"
    ),
    bg: bool = typer.Option(
        False, "--bg", help="Run as background process"
    ),
    stop: bool = typer.Option(
        False, "--stop", help="Stop background daemon"
    ),
    auto_apply: bool = typer.Option(
        False, "--auto-apply", help="Auto-apply high-value learnings"
    ),
    template: str = typer.Option(
        "E:\\projects\\template-base", "--template", "-t", help="Template path"
    ),
):
    """Start/stop the periodic harvest daemon."""
    from src.core.harvest_daemon import HarvestDaemon

    if stop:
        if HarvestDaemon.stop():
            typer.echo("Daemon stopped.")
        else:
            typer.echo("No daemon running.")
        return

    if bg:
        pid = HarvestDaemon.start_background(
            interval=interval, template_path=template
        )
        typer.echo(f"Daemon started in background (PID: {pid})")
        return

    daemon = HarvestDaemon(
        interval=interval,
        auto_apply=auto_apply,
        template_path=template,
    )
    typer.echo(
        f"Starting daemon (interval={interval}s, auto_apply={auto_apply})"
    )
    typer.echo("Press Ctrl+C to stop.")
    daemon.start()


def main():
    _ensure_observability()
    app()


if __name__ == "__main__":
    main()
