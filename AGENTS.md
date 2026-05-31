# Agent Notes

## Project Purpose
This repository implements Experiment 2, "Bring Your Own Agent" (BYOA), for the software product practice course.

## How To Run
- Run tests: `python -m unittest discover -s tests`
- List tool schemas: `python -m byoa_agent tools`
- Run the DeepSeek demo: `DEEPSEEK_API_KEY=... python -m byoa_agent demo`

## Constraints
- Keep the agent single-purpose: it should help understand and complete the BYOA experiment.
- Keep local tools restricted to the parent course workspace.
- Do not commit real API keys or generated run logs.
- Prefer standard-library Python unless a dependency clearly improves the experiment.

