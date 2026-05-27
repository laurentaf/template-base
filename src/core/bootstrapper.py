"""Bootstrap Engine — First-Run Project Initialization.

When template-base is copied to a new project:
1. Detect fresh project (no .harness_state.json or PROJECT_NAME=template-base)
2. Substitute template variables ({{PROJECT_NAME}}, {{EXECUTION_TIER}})
3. Create missing directories and __init__.py files
4. Create .template-info.json for future sync
5. Generate opencode.json from template
6. Check infrastructure health
7. Print status report
"""

import asyncio
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from src.core.config import settings
from src.core.local_backend import check_redis


class HealthChecker:
    SERVICES = {
        "Redis": {
            "url_env": "REDIS_URL",
            "default": "redis://localhost:6379",
            "check": "redis",
        },
        "PostgreSQL": {
            "url_env": "DATABASE_URL",
            "default": "",
            "check": "postgres",
        },
        "Phoenix": {
            "url_env": "PHOENIX_URL",
            "default": "http://localhost:6006",
            "check": "http",
        },
        "NIM Bridge": {
            "url_env": "NIM_BRIDGE_URL",
            "default": "http://localhost:8081/v1/chat/completions",
            "check": "http",
        },
        "Qdrant": {
            "url_env": "QDRANT_URL",
            "default": "http://localhost:6333",
            "check": "http",
        },
        "MinIO": {
            "url_env": "MINIO_URL",
            "default": "http://localhost:9000",
            "check": "http",
        },
    }

    @staticmethod
    async def check_all() -> dict[str, dict[str, Any]]:
        results: dict[str, dict[str, Any]] = {}
        for name, info in HealthChecker.SERVICES.items():
            url = os.environ.get(info["url_env"], info["default"])
            if info["check"] == "redis":
                ok = await check_redis(url)
                results[name] = {
                    "url": url,
                    "status": "OK" if ok else "DOWN",
                    "required": name == "Redis",
                }
            elif info["check"] == "http":
                ok = await HealthChecker._check_http(url)
                results[name] = {
                    "url": url,
                    "status": "OK" if ok else "DOWN",
                    "required": False,
                }
            elif info["check"] == "postgres":
                ok = await HealthChecker._check_postgres(url)
                results[name] = {
                    "url": "***" if ok else url,
                    "status": "OK" if ok else "DOWN",
                    "required": False,
                }
        return results

    @staticmethod
    async def _check_http(url: str) -> bool:
        try:
            import httpx

            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(url.split("/v1/")[0] if "/v1/" in url else url)
                return resp.status_code < 500
        except Exception:
            return False

    @staticmethod
    async def _check_postgres(url: str) -> bool:
        try:
            import psycopg

            conn = psycopg.connect(url, connect_timeout=3)
            conn.close()
            return True
        except Exception:
            return False

    @staticmethod
    async def run_and_print():
        results = await HealthChecker.check_all()
        print("\n=== Service Health Check ===\n")
        print(f"{'Service':<15} {'Status':<8} {'URL'}")
        print("-" * 60)
        for name, info in results.items():
            req = " *" if info["required"] else ""
            print(f"{name:<15} {info['status']:<8} {info['url']}{req}")
        ok_count = sum(1 for i in results.values() if i["status"] == "OK")
        print(f"\n{ok_count}/{len(results)} services available")
        if ok_count == 0:
            print("\nNo services running. Start infrastructure:")
            print("  docker compose up -d")
        elif not results.get("Redis", {}).get("status") == "OK":
            print("\nRedis is required for distributed mode. Agents will use local mode.")


class AgentManager:
    AGENT_TYPES = ["orchestrator", "data-pipeline", "analytics", "code-gen", "reviewer"]
    AGENT_MODULES = {
        "orchestrator": "src.agents.orchestrator",
        "data-pipeline": "src.agents.data_pipeline_agent",
        "analytics": "src.agents.analytics_agent",
        "code-gen": "src.agents.code_gen_agent",
        "reviewer": "src.agents.reviewer_agent",
    }
    _processes: list[subprocess.Popen] = []
    _pid_dir = Path.home() / ".ltade" / "agents"

    @classmethod
    def _save_pids(cls):
        cls._pid_dir.mkdir(parents=True, exist_ok=True)
        pid_file = cls._pid_dir / "pids.json"
        pids = [
            {"pid": p.pid, "module": m} for p, m in zip(cls._processes, cls.AGENT_MODULES.values())
        ]
        pid_file.write_text(json.dumps(pids))

    @classmethod
    def _cleanup_stale_pids(cls):
        pid_file = cls._pid_dir / "pids.json"
        if not pid_file.exists():
            return
        try:
            pids = json.loads(pid_file.read_text())
            for entry in pids:
                try:
                    proc = subprocess.Popen(
                        ["tasklist", "/FI", f"PID eq {entry['pid']}"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                    )
                    proc.wait(timeout=5)
                except Exception:
                    pass
            pid_file.unlink()
        except Exception:
            pass

    @staticmethod
    async def start_agents(types_str: str = "all", mode: str = "auto"):
        if types_str == "all":
            types = AgentManager.AGENT_TYPES
        else:
            types = [
                t.strip() for t in types_str.split(",") if t.strip() in AgentManager.AGENT_TYPES
            ]

        print(f"\n=== Starting Agents (mode={mode}) ===\n")
        for agent_type in types:
            module = AgentManager.AGENT_MODULES.get(agent_type)
            if not module:
                print(f"  Unknown agent type: {agent_type}")
                continue
        try:
            proc = subprocess.Popen(
                ["python", "-m", module],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            AgentManager._processes.append(proc)
            print(f" Started {agent_type} (PID {proc.pid})")
            AgentManager._save_pids()
        except Exception as e:
            print(f"  Failed to start {agent_type}: {e}")

        print(f"\n{len(AgentManager._processes)} agents running. Press Ctrl+C to stop.")
        try:
            await asyncio.sleep(float("inf"))
        except (KeyboardInterrupt, asyncio.CancelledError):
            await AgentManager.stop_agents()

    @staticmethod
    async def stop_agents():
        print("\n=== Stopping Agents ===\n")
        for proc in AgentManager._processes:
            try:
                proc.terminate()
                proc.wait(timeout=5)
                print(f"  Stopped PID {proc.pid}")
            except Exception:
                proc.kill()
        AgentManager._processes.clear()
        AgentManager._cleanup_stale_pids()
        print("All agents stopped.")

    @staticmethod
    async def show_status():
        from src.core.local_backend import check_redis

        redis_ok = await check_redis()
        if not redis_ok:
            print("Redis not available — agents running in local mode only.")
            print("Start Redis with: docker compose up -d redis")
            return

        try:
            from src.core.agent_registry import AgentRegistry

            registry = AgentRegistry()
            await registry.connect()
            agents = await registry.discover()
            if not agents:
                print("No agents registered. Start agents with: ltade agents start")
                return
            print("\n=== Agent Status ===\n")
            print(f"{'Agent ID':<30} {'Type':<15} {'Status':<10} {'Capabilities'}")
            print("-" * 80)
            for a in agents:
                caps = ", ".join(a.get("capabilities", [])[:3])
                print(f"{a['agent_id']:<30} {a['agent_type']:<15} {a['status']:<10} {caps}")
            print(f"\n{len(agents)} agents registered")
        except Exception as e:
            print(f"Could not reach registry: {e}")


class BootstrapEngine:
    TEMPLATE_VARS = {
        "PROJECT_NAME": "ai-data-project",
        "EXECUTION_TIER": "development",
    }
    DIRS_TO_CREATE = [
        "spec/build",
        "spec/archive",
        "data/sample",
        "data/exports",
        "transform/models",
        "logs",
    ]
    INIT_FILES = [
        "src/__init__.py",
        "src/core/__init__.py",
        "src/agents/__init__.py",
        "src/tools/__init__.py",
        "src/schemas/__init__.py",
        "src/rag/__init__.py",
        "src/pipelines/__init__.py",
        "src/pipelines/medallion/__init__.py",
        "cli/__init__.py",
    ]

    def __init__(
        self,
        project_name: str | None = None,
        tier: str = "development",
        skip_infra: bool = False,
        yes: bool = False,
    ):
        self.project_name = project_name
        self.tier = tier
        self.skip_infra = skip_infra
        self.yes = yes
        self.root = Path.cwd()

    def _is_fresh_project(self) -> bool:
        harness = self.root / ".harness_state.json"
        if not harness.exists():
            return True
        try:
            data = json.loads(harness.read_text())
            if data.get("project") in ("template-base", "ai-data-project"):
                return True
        except Exception:
            pass
        return False

    def _substitute_template_vars(self, project_name: str):
        replacements = {
            "{{PROJECT_NAME}}": project_name,
            "{{EXECUTION_TIER}}": self.tier,
            "template-base": project_name,
        }
        files_to_check = [
            self.root / "GROUNDING.md",
            self.root / "pyproject.toml",
            self.root / "README.md",
            self.root / ".env.example",
            self.root / "MEMORY.md",
        ]
        for fpath in files_to_check:
            if not fpath.exists():
                continue
            content = fpath.read_text(encoding="utf-8")
            modified = False
            for old, new in replacements.items():
                if old in content:
                    content = content.replace(old, new)
                    modified = True
            if modified:
                fpath.write_text(content, encoding="utf-8")

    def _ensure_required_files(self):
        agent_system = self.root / "AGENT_SYSTEM.md"
        if not agent_system.exists():
            raise FileNotFoundError(
                "AGENT_SYSTEM.md is MISSING from project root. "
                "This file is mandatory. Bootstrap refused. "
                "Copy it from the template or create it before re-running."
            )

    def _create_directories(self):
        for dir_path in self.DIRS_TO_CREATE:
            full = self.root / dir_path
            full.mkdir(parents=True, exist_ok=True)
            gitkeep = full / ".gitkeep"
            if not gitkeep.exists():
                gitkeep.write_text("")

    def _create_init_files(self):
        for init_path in self.INIT_FILES:
            full = self.root / init_path
            if not full.exists():
                full.write_text("")

    def _create_harness_state(self, project_name: str):
        harness = self.root / ".harness_state.json"
        state = {
            "project": project_name,
            "created_at": datetime.now().isoformat(),
            "last_deployment": None,
            "active_specs": [],
            "github_repo": None,
            "health": "OK",
            "execution_tier": self.tier,
            "bootstrapped": True,
            "bootstrap_version": "1.0.0",
        }
        harness.write_text(json.dumps(state, indent=2))

    def _create_template_info(self):
        from src.core.template_sync import get_git_commit, save_template_info, scan_template

        template_root = settings.template_path
        try:
            files = scan_template(template_root)
            commit = get_git_commit(template_root)
            save_template_info(str(self.root), template_root, commit, files)
        except Exception:
            pass

    def _generate_opencode_json(self, project_name: str):
        config_path = self.root / "opencode.json"
        if config_path.exists():
            return
        config = {
            "project": project_name,
            "model": "nvidia/deepseek-ai/deepseek-v4-flash",
            "agent": {
                "primary": "data-engineer",
            },
            "mcp": {
                "filesystem": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-filesystem", str(self.root)],
                },
                "github": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-github"],
                    "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"},
                },
                "postgres": {
                    "command": "npx",
                    "args": ["-y", "@anthropic/mcp-server-postgres", settings.DATABASE_URL],
                },
                "docker": {
                    "command": "npx",
                    "args": ["-y", "@anthropic/mcp-server-docker"],
                },
                "sequential-thinking": {
                    "command": "npx",
                    "args": ["-y", "@anthropic/mcp-server-sequential-thinking"],
                },
            },
            "hooks": {
                "on_start": "ltade init --check",
            },
        }
        config_path.write_text(json.dumps(config, indent=2))

    async def run(self):
        if not self._is_fresh_project():
            print("Project already initialized. Use 'ltade health' to check status.")
            return

        project_name = self.project_name
        if not project_name:
            dir_name = self.root.name
            if self.yes:
                project_name = dir_name
            else:
                project_name = input(f"Project name [{dir_name}]: ").strip() or dir_name

        print(f"\n=== Bootstrapping: {project_name} ===\n")

        print(" Checking required files...")
        self._ensure_required_files()

        print(" Substituting template variables...")
        self._substitute_template_vars(project_name)

        print("  Creating directories...")
        self._create_directories()

        print("  Creating __init__.py files...")
        self._create_init_files()

        print("  Creating harness state...")
        self._create_harness_state(project_name)

        print("  Creating opencode.json...")
        self._generate_opencode_json(project_name)

        print("  Creating .template-info.json...")
        self._create_template_info()

        if not self.skip_infra:
            print("\n  Checking infrastructure...")
            await HealthChecker.run_and_print()

        print(f"\n=== Bootstrap Complete: {project_name} ===")
        print("  Next steps:")
        print("    1. opencode .          — Start the AI agent")
        print("    2. ltade agents start  — Start runtime agents")
        print("    3. ltade health        — Check service status")
