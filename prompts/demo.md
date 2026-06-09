Run the full BYOA course-task demo for the already implemented `byoa-course-agent` project.

Important context:
- The agent purpose has already been chosen: BYOA Code, a Claude Code style course-task coding agent.
- The implementation uses DeepSeek OpenAI-compatible Function Calling with SSE streaming, not a separate MCP server.
- The main user interface is the interactive terminal shell started with `python -m byoa_agent`.
- The implemented local tools are `read_file`, `write_file`, `edit_file`, `list_files`, `grep_files`, `run_command`, `extract_pptx_text`, `extract_docx_text`, `search_extracted_context`, `check_submission_readiness`, and `summarize_tool_log`.
- This project does not use Pydantic. It uses explicit OpenAI-compatible JSON Schema dictionaries in Python.
- The supported commands are `python -m byoa_agent` (interactive chat, default), plus the `ask`, `check`, `report`, `demo`, and `tools` subcommands.
- The test command is `python -m unittest discover -s tests`; do not recommend pytest.
- Do not tell the student to choose a new agent purpose or start scaffolding from scratch.
- Write the final answer in Chinese.

Steps:
1. List available PPTX and DOCX files with `list_files`.
2. List this repository's files and verify that README, prompts, source code, tests, report draft, and run log directories exist.
3. Read `Week 13-15.pptx` and find the Experiment 2 requirements.
4. Run `check_submission_readiness` to verify rubric-facing repository evidence.
5. Summarize `runs/latest.jsonl` with `summarize_tool_log` if present.
6. Search the loaded context for `Bring Your Own Agent` and `Rubric`.
7. Produce:
   - a concise requirement summary,
   - a checklist of what this repository already satisfies and what remains before submission,
   - a 95+ scoring-oriented screenshot plan using the actual commands/files in this repository,
   - a short Chinese Markdown report outline tailored to the interactive CLI agent.
