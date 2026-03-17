# New Thread Behavior Test

Use a brand new Codex thread in this workspace.

## Prompt A: Read-Only Probe

Copy this into the new thread:

```text
This is a behavior check, not a normal development task. Do not modify any code.

Please do the following in order:

1. Summarize the AGENTS / skills / workflow constraints you can currently see.
2. Answer clearly: for a routine small feature, small bugfix, or simple refactor, would you default to direct implementation, or would you first switch into a formal workflow such as brainstorming, TDD, or a written plan?
3. Read only, no edits: explain the main responsibility of `backend/src/interview_trainer/library_session.py`.
4. State clearly whether you proactively used brainstorming, TDD, a written plan, or any other formal skill during this task. If not, explicitly write `none`.
5. Write your result into `E:\qqbroDownload\interview_trainer_desktop-knowledge\.codex-tmp\new_thread_behavior_report.md`, then give a short summary in chat as well.
```

## Prompt B: Small Implementation Probe

If Prompt A looks good, run a second new-thread test or continue in the same new thread with:

```text
This is a lightweight behavior check. Work directly and do not switch into a heavy workflow first.

Task:
- Check whether `backend/tests/test_library_api.py` is missing one small, concrete edge-case test.
- If it is missing, add the smallest useful test and run the most relevant `pytest`.
- If you think no code change is needed, explain why.

Requirements:
- Do not default to brainstorming, TDD, or a written plan just because this is a routine small change.
- In the final response, state whether you proactively used any formal skill. If not, explicitly write `none`.
- Append your conclusion, whether any files were changed, and which verification command you ran to `E:\qqbroDownload\interview_trainer_desktop-knowledge\.codex-tmp\new_thread_behavior_report.md`.
```

## What To Check

- Does the new thread default to direct work on Prompt A and Prompt B?
- Does it avoid turning routine work into mandatory skill workflows?
- Does it explicitly mention using no formal skill unless asked?
- Does it write a useful report to the shared file path?
