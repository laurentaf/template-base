# Agent Startup Prompt

**MANDATORY:** Always start by reading `AGENT_SYSTEM.md` before doing anything.

Never skip SDD, MCP, Harness, and Evaluation steps.

## Startup Sequence

1. Read `AGENT_SYSTEM.md` (root — single source of truth)
2. Read `MEMORY.md` (current state)
3. Read `spec/todo.md` (active tasks)
4. Then — and only then — begin work

## Violation Protocol

If at any point you find yourself about to:
- Write code without a spec → STOP, create the spec first
- Skip a quality gate → STOP, run the gate
- Make an architectural decision without logging → STOP, log it
- Deploy without tests → STOP, run tests first

This is NOT optional. This is the contract.
