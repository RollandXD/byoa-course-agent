Run the full BYOA course-task demo for the already implemented `byoa-course-agent` project.

Important context:
- The agent purpose has already been chosen: it is a course-task assistant for Experiment 2.
- The implementation already uses DeepSeek OpenAI-compatible Function Calling, not a separate MCP server.
- The implemented local tools are `list_workspace_files`, `list_project_files`, `extract_pptx_text`, `extract_docx_text`, and `search_extracted_context`.
- This project does not use Pydantic. It uses explicit OpenAI-compatible JSON Schema dictionaries in Python.
- The supported commands are `python -m byoa_agent tools`, `python -m byoa_agent demo`, and `python -m byoa_agent ask "<prompt>"`.
- The test command is `python -m unittest discover -s tests`; do not recommend pytest.
- Do not tell the student to choose a new agent purpose or start scaffolding from scratch.
- Write the final answer in Chinese.

Steps:
1. List available PPTX and DOCX files.
2. List this project repository's files and verify that README, prompts, source code, tests, and report draft files exist.
3. Read `Week 13-15.pptx` and find the Experiment 2 requirements.
4. Read the previous experiment report DOCX to identify report style and identity information.
5. Search the loaded context for `Bring Your Own Agent` and `Rubric`.
6. Produce:
   - a concise requirement summary,
   - a checklist of what this repository already satisfies and what remains before submission,
   - 3 to 4 screenshot suggestions using the actual commands/files in this repository,
   - a short Chinese Markdown report draft outline tailored to this project.
