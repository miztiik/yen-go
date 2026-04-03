# Git Safety Prompt for AI Agents

Copy and paste this at the start of your conversation with an agent.

---

```
CRITICAL GIT SAFETY RULES - READ BEFORE ANY GIT OPERATIONS

This repository has multiple agents working concurrently. Untracked files (crawler output, runtime data) will be PERMANENTLY DESTROYED by careless git operations.

## FORBIDDEN COMMANDS (NEVER USE)
- git stash (any variant)
- git reset --hard
- git clean -fd
- git checkout .
- git restore .
- git add .
- git add -A

## SAFE COMMIT WORKFLOW

When you need to commit your changes:

1. FIRST check for untracked files outside your scope:
   git status --porcelain | grep "^??"

   If you see files in external-sources/, .pm-runtime/, or tools/*/output/ - these are NOT yours. DO NOT touch them.

2. Stage ONLY your specific files by explicit path:
   git add path/to/your/file1.ts path/to/your/file2.py

3. Verify staged files are ONLY yours:
   git diff --cached --name-only
   If you see unexpected files, unstage them: git reset HEAD <file>

4. Create feature branch and commit:
   git checkout -b feature/your-change-name
   git commit -m "feat: your description"

5. Merge back to main:
   git checkout main
   git merge --no-ff feature/your-change-name

## IF YOU NEED TO SWITCH BRANCHES WITH UNCOMMITTED WORK
DO NOT use git stash. ASK ME how to proceed.

## PROTECTED DIRECTORIES (DO NOT DELETE)
- external-sources/*/sgf/ - Crawled puzzles (hours to regenerate)
- external-sources/*/logs/ - Crawl history (lost forever)


If any of your git operations would affect these directories, STOP and ask me first.
```

---

## See Also

- [CLAUDE.md](../../CLAUDE.md) - Git Safety Rules section
- [copilot-instructions.md](../../.github/copilot-instructions.md) - Full agent guidelines

---

_Last Updated: 2026-02-15_
