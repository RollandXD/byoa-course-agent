# Agent Notes

## Project Purpose
This repository implements Experiment 2, "Bring Your Own Agent" (BYOA), for the software product practice course. The deliverable is BYOA Code: a Claude Code style terminal agent driven by DeepSeek Function Calling.

## How To Run
- Run tests: `python -m unittest discover -s tests`
- Start the interactive shell: `DEEPSEEK_API_KEY=... python -m byoa_agent`
- List tool schemas: `python -m byoa_agent tools`
- Run the DeepSeek demo: `DEEPSEEK_API_KEY=... python -m byoa_agent demo`

## Architecture
- `src/byoa_agent/agent.py`: persistent multi-turn session loop with context compaction.
- `src/byoa_agent/deepseek.py`: OpenAI-compatible client, including SSE streaming with tool_calls fragment reassembly.
- `src/byoa_agent/tools/`: registry-decorated toolbox; `general.py` holds coding tools, `course.py` holds course skills.
- `src/byoa_agent/permissions.py`: y/n/always gate for write_file, edit_file, and run_command.
- `src/byoa_agent/chat.py` + `ui.py`: interactive shell with slash commands, `@file` mentions, `!cmd` passthrough, streaming markdown rendering, spinner, diff previews, and turn stats.

## Constraints
- Keep the agent single-purpose: it should help understand and complete the BYOA experiment.
- Reads are sandboxed to the parent course workspace; writes and shell commands are sandboxed to this repository and must pass the permission gate.
- Do not commit real API keys or generated run logs.
- Prefer standard-library Python unless a dependency clearly improves the experiment. No Pydantic, no pytest.
