"""
End-to-end demo: generate data -> Medallion pipeline -> analyze.

Run:
    uv run python scripts/run_demo.py
"""

import subprocess
import sys
from pathlib import Path

from src.core.telemetry import setup_observability


def step(label: str):
    print(f"\n{'=' * 60}")
    print(f"  {label}")
    print(f"{'=' * 60}")


def sh(cmd: str):
    print(f"  $ {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ERROR: {result.stderr.strip()}")
        sys.exit(1)
    out = result.stdout.strip()
    if out:
        for line in out.split("\n"):
            print(f"    {line}")
    return out


def main():
    setup_observability("demo")

    # Step 1: Generate synthetic data
    step("1/5: Generating synthetic e-commerce data")
    sh("uv run python -m data.generators.ecommerce")
    sample_dir = Path("data/sample")
    files = list(sample_dir.glob("*.csv"))
    print(f"    Files: {', '.join(f.name for f in files)}")

    # Step 2: Run Medallion pipeline
    step("2/5: Running Medallion pipeline (Bronze -> Silver -> Gold)")
    sh("uv run python -m src.pipelines.medallion.run")

    # Step 3: FlowCheck status
    step("3/5: FlowCheck pipeline health dashboard")
    sh("uv run python -m cli.flowcheck status")

    # Step 4: Quality checks
    step("4/5: Data quality on customers")
    sh("uv run python -m cli.flowcheck quality customers")

    # Step 5: AI description
    step("5/5: AI-powered dataset description")
    print("    (uses LLM via NIM Bridge or OpenRouter)")
    from src.core.llm import llm

    try:
        resp = llm.chat(
            [
                {
                    "role": "user",
                    "content": (
                        "I just ran a Medallion pipeline with e-commerce data: "
                        "customers, products, orders, transactions went through "
                        "Bronze (raw) -> Silver (cleansed) -> Gold (analytics). "
                        "What kind of analyses and insights can I now run?"
                    ),
                }
            ]
        )
        print(f"\n{resp.content}")
        print(
            f"\n    (model: {resp.model}, tokens: {resp.input_tokens + resp.output_tokens}, "
            f"latency: {resp.latency_ms}ms)"
        )
    except RuntimeError as e:
        print(f"    ⚠️ LLM unavailable (NIM/OpenRouter keys may not be set): {e}")

    print(f"\n{'=' * 60}")
    print("  Demo complete!")
    print(f"{'=' * 60}")
    print("  What was done:")
    print("    - Generated synthetic e-commerce CSV data")
    print("    - Ingested into Bronze layer (raw DuckDB)")
    print("    - Transformed to Silver layer (dedup, audit cols, quality checks)")
    print("    - Built Gold analytics views")
    print("    - Checked pipeline health with FlowCheck")
    print("    - Ran data quality validation")
    print("")
    print("  Next: uv run python src/main.py describe orders")
    print("        uv run python src/main.py pipeline")


if __name__ == "__main__":
    main()
