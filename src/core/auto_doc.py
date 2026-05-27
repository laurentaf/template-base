"""Auto-Documentation Generator.

After every task completion, updates project documentation:
1. docs/knowledge_base.md with new facts
2. .opencode/context/default/knowledge.md entry points
3. .opencode/context/default/architecture.md component map
4. spec/design.md if architecture changed
"""

from datetime import datetime
from pathlib import Path
from typing import Any

from src.core.llm import llm


class AutoDoc:
    @staticmethod
    def update_after_task(task_type: str, task_result: dict[str, Any], agent_type: str):
        try:
            AutoDoc._update_knowledge_base(task_type, task_result, agent_type)
        except Exception:
            pass

        try:
            AutoDoc._update_context_knowledge(task_type, task_result, agent_type)
        except Exception:
            pass

    @staticmethod
    def _update_knowledge_base(task_type: str, task_result: dict[str, Any], agent_type: str):
        kb_path = Path("docs/knowledge_base.md")
        if not kb_path.exists():
            return

        content = kb_path.read_text(encoding="utf-8")
        entry = f"\n## {datetime.now().strftime('%Y-%m-%d')} — {task_type} ({agent_type})\n\n"
        if isinstance(task_result, dict):
            for key, value in task_result.items():
                if key in ("report", "description", "sql", "content"):
                    entry += f"**{key}:** {str(value)[:500]}\n\n"
        entry += f"*Auto-documented by {agent_type}*\n"

        marker = "<!-- AUTO_DOC -->"
        if marker in content:
            content = content.replace(marker, f"{marker}{entry}")
        else:
            content += f"\n{marker}\n{entry}"

        kb_path.write_text(content, encoding="utf-8")

    @staticmethod
    def _update_context_knowledge(task_type: str, task_result: dict[str, Any], agent_type: str):
        ctx_path = Path(".opencode/context/default/knowledge.md")
        if not ctx_path.exists():
            return

        content = ctx_path.read_text(encoding="utf-8")
        last_updated = f"last_updated: {datetime.now().strftime('%Y-%m-%d')}"
        if "last_updated:" in content:
            import re

            content = re.sub(r"last_updated: \d{4}-\d{2}-\d{2}", last_updated, content)
        else:
            content += f"\n\n{last_updated}\n"

        ctx_path.write_text(content, encoding="utf-8")

    @staticmethod
    def update_architecture(component: str, description: str, technology: str):
        arch_path = Path(".opencode/context/default/architecture.md")
        if not arch_path.exists():
            return

        content = arch_path.read_text(encoding="utf-8")
        if "## Component Map" in content and "[Describe" in content:
            table_header = (
                "| Component | Responsibility | Technology |\n"
                "|-----------|---------------|------------|\n"
            )
            table_row = f"| {component} | {description} | {technology} |\n"
            content = content.replace(
                "[Describe the main components and their relationships]",
                table_header + table_row,
            )
        elif "## Component Map" in content:
            table_row = f"| {component} | {description} | {technology} |\n"
            insert_pos = content.find("| Component |")
            if insert_pos > 0:
                header_end = content.find("\n", content.find("|-----------|", insert_pos)) + 1
                content = content[:header_end] + table_row + content[header_end:]

        arch_path.write_text(content, encoding="utf-8")

    @staticmethod
    async def generate_readme_section(section_title: str, content_generator_prompt: str) -> str:
        try:
            prompt = (
                f"Generate a README.md section titled '{section_title}' for this project.\n"
                f"{content_generator_prompt}\n"
                "Use markdown format. Be concise."
            )
            resp = llm.chat([{"role": "user", "content": prompt}], max_tokens=1024)
            return resp.content
        except Exception:
            return ""


auto_doc = AutoDoc()
