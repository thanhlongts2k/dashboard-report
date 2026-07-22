# Rules for Report2026 Workspace

## 1. CheckList.md SOP Compliance
- **MANDATORY**: BEFORE submitting any work, proposing plans, or requesting commit approval, you MUST read the file [CheckList.md](file:///d:/Sources/dashboard-report/CheckList.md) and verify that all 5 steps of the Standard Operating Procedure (SOP) are fully satisfied.
- **Commit Approval**: Never run a git commit command or ask to finalize without verifying Step 3 (Documentation updated in DocumentAPI_Report2026.md and target.md) and Step 5 (explicit user approval for commit).

## 2. Modification Logging & Handoff Continuity (Strict Requirement)
- **MANDATORY TRACKING**: Before making ANY modifications to the codebase or architecture, you MUST create or update a tracking file named `HANDOVER_LOG.md` (or update an existing one) in the root directory.
- **What to Log**: Every time you start a change, you must document:
  1. **Current Objective**: What is the specific task you are trying to accomplish?
  2. **Planned Modifications**: What files are you planning to change and what is the specific logic/code to be altered?
  3. **Current Status**: Update this as you work (e.g., "Pending", "In Progress: modifying file X", "Completed").
- **The Purpose (Quota/Interrupt Resilience)**: Do not skip this step. This log exists so that if your execution is interrupted (e.g., API quota exceeded, token limits reached, session closed), the next AI agent can immediately read `HANDOVER_LOG.md`, understand exactly where you left off, and resume the work seamlessly without requiring the user to re-explain the context.

## 3. Token & Quota Efficiency Rules (Strict Optimization)
- **Silent & Concise Output**: Never print massive raw logs or dataframes into the chat context. Output heavy debug data to temporary scratch files (`scratch/`) and summarize only key insights in natural language.
- **Targeted Code Reading**: Specify explicit line ranges (`StartLine`/`EndLine`) when viewing large files (e.g. `models.py`, `views.py`) to prevent context bloat.
- **Memory Persistence**: Always document discovered repo-specific logic, MISA mapping quirks, or DB schema exceptions in `target.md` or `Accounting_Tracking_History.md` so subsequent agents do not spend quota re-investigating.

## 4. Context Isolation & Tool Script Reusability
- **Subagent Delegation**: Delegate heavy exploratory tasks, multi-file scans, or long web/log audits to Subagents. Subagents run in isolated context windows and return concise summaries to keep the primary chat context clean.
- **Reusable Utility Scripts**: Place recurring diagnostic or data-export scripts in `scripts/` instead of re-authoring duplicate inline Python code snippets continuously.
- **Fail-Fast Pre-Validation**: Run lightweight syntax checks (`python -m py_compile ...` or `python manage.py check`) before launching heavy execution tasks to avoid wasted API calls on trivial errors.