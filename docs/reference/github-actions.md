# GitHub Actions Reference

This page is for **developers and contributors** who need to understand Yen-Go's CI/CD workflows.

Yen-Go uses GitHub Actions for automated puzzle generation and deployment. All workflows run in GitHub's cloud infrastructure.

## In This Document

- [Workflow Overview](#workflow-overview)
- [Daily Generation Workflow](#daily-generation-workflow)
- [Deploy Workflow](#deploy-workflow)
- [Troubleshooting](#troubleshooting)

---

## Workflow Overview

| Workflow                                       | File                   | Trigger              | Purpose                                          |
| ---------------------------------------------- | ---------------------- | -------------------- | ------------------------------------------------ |
| [Daily Generation](#daily-generation-workflow) | `daily-generation.yml` | Daily cron, manual   | Generate and validate daily puzzles, then deploy |
| [Deploy](#deploy-workflow)                     | `deploy.yml`           | Push to main, manual | Build and deploy frontend to GitHub Pages        |

---

## Daily Generation Workflow

**File**: [`.github/workflows/daily-generation.yml`](../../.github/workflows/daily-generation.yml)

Generates daily puzzle challenges, validates them, and deploys to GitHub Pages automatically.

### What It Does

1. **Generate**: Creates puzzles for the specified date (or today)
2. **Validate**: Ensures all puzzles are valid before publishing (invalid puzzles are skipped)
3. **Commit**: Pushes generated puzzles to `yengo-puzzle-collections/`
4. **Deploy**: Automatically deploys to GitHub Pages after successful generation

### Triggers

| Trigger   | When                                     |
| --------- | ---------------------------------------- |
| Scheduled | `00:00 UTC` daily                        |
| Manual    | Via Actions tab with optional date input |

### Jobs

| Job        | Description                                      | Runs After |
| ---------- | ------------------------------------------------ | ---------- |
| `generate` | Run puzzle manager daily command, commit changes | -          |
| `deploy`   | Deploy updated site to GitHub Pages              | `generate` |

### Steps

1. 📥 Checkout repository (full depth)
2. ⚙️ Setup Python 3.11
3. 📦 Install puzzle manager (`pip install -e .`)
4. 📅 Determine date (from input or today's UTC date)
5. 🧩 Generate & validate puzzles (`python -m backend.puzzle_manager daily --date $DATE`)
6. 📤 Commit and push changes
7. 🚀 Deploy to GitHub Pages (automatic after generation)

### Output Location

Generated puzzles are written to:

```
yengo-puzzle-collections/
├── sgf/{NNNN}/{content_hash}.sgf
├── yengo-search.db          ← includes daily_schedule + daily_puzzles tables
├── yengo-content.db
└── db-version.json
```

Daily generation writes schedule and puzzle rows directly into `yengo-search.db` (DB-1). CI commits `yengo-search.db` + `db-version.json`.

### Manual Trigger

To generate puzzles for a specific date:

1. Go to **Actions** tab in GitHub
2. Select **Daily Puzzle Generation**
3. Click **Run workflow**
4. Enter date in `YYYY-MM-DD` format (optional, defaults to today)
5. Click **Run workflow**

### Failure Notifications

If the workflow fails, it automatically creates a GitHub issue with:

- Failure date
- Link to the failed workflow run

---

## Deploy Workflow

**File**: [`.github/workflows/deploy.yml`](../../.github/workflows/deploy.yml)

Deploys the frontend to GitHub Pages. This workflow runs on push to `main` or can be triggered manually. Note: Daily Generation has its own deploy job that runs automatically after puzzle generation.

### Triggers

| Trigger | When             |
| ------- | ---------------- |
| Push    | To `main` branch |
| Manual  | Via Actions tab  |

### Concurrency

- Only one deployment runs at a time
- New pushes cancel in-progress deployments

### Jobs

| Job          | Description                                | Runs After |
| ------------ | ------------------------------------------ | ---------- |
| `build`      | Build frontend, run tests, upload artifact | -          |
| `deploy`     | Deploy artifact to GitHub Pages            | `build`    |
| `lighthouse` | Audit deployed site                        | `deploy`   |

### Steps

1. 📥 Checkout repository
2. ⚙️ Setup Node.js 20
3. 📦 Install dependencies (`npm ci`)
4. 📁 Copy puzzles to public folder
5. 🔨 Build frontend (`npm run build`)
6. 🧪 Run tests
7. 🚀 Deploy to GitHub Pages

### Manual Trigger

1. Go to **Actions** tab in GitHub
2. Select **Deploy to GitHub Pages**
3. Click **Run workflow**
4. Select branch (usually `main`)
5. Click **Run workflow**

---

## Troubleshooting

### Daily Generation Issues

**Symptoms**: Daily puzzles not appearing, missing dates in daily view.

| Issue                 | Cause                                          | Solution                                                         |
| --------------------- | ---------------------------------------------- | ---------------------------------------------------------------- |
| Puzzles not appearing | Workflow runs at **00:00 UTC**, not local time | Wait for UTC midnight or trigger manually                        |
| Failed silently       | Workflow error                                 | Check **Actions** tab for failed runs (creates issue on failure) |
| No puzzles generated  | Source pool exhausted for difficulty level     | Check puzzle manager logs                                        |

**Check If Workflow Ran**:

1. Go to **Actions** tab
2. Select **Daily Puzzle Generation**
3. Review recent runs for the expected date

**Manual Regeneration**:

```bash
# Via GitHub Actions UI:
# 1. Actions → Daily Puzzle Generation → Run workflow
# 2. Enter date: 2026-01-28

# Or run locally:
cd backend/puzzle_manager
python -m backend.puzzle_manager daily --date 2026-01-28
```

### Deployment Not Triggering

**Symptoms**: Merged PR but site not updated.

| Issue                 | Solution                                                     |
| --------------------- | ------------------------------------------------------------ |
| PR not merged to main | Deployment only triggers on push to `main`                   |
| Workflow disabled     | Check **Actions** tab → Deploy workflow → Enable if disabled |
| Concurrent deployment | Previous deployment may have cancelled yours                 |

**Manual Trigger**:

1. Go to **Actions** → **Deploy to GitHub Pages**
2. Click **Run workflow** → Select `main` → **Run workflow**

### Workflow Permissions Error

**Symptoms**: Workflow fails with permission denied.

**Solution**: Ensure repository settings allow Actions to write:

1. Go to **Settings** → **Actions** → **General**
2. Under "Workflow permissions", select **Read and write permissions**

---

## Environment Variables

| Variable         | Description                                     |
| ---------------- | ----------------------------------------------- |
| `GITHUB_TOKEN`   | Auto-provided, used for commits and deployments |
| `PYTHONPATH`     | Set to workspace root for Python imports        |
| `NODE_ENV`       | Set to `production` for frontend builds         |
| `PYTHON_VERSION` | `3.11` (defined in workflow)                    |
| `NODE_VERSION`   | `20` (defined in workflow)                      |

---

## See Also

- [Development Setup](../getting-started/develop.md) — Local development workflow
- [Architecture Overview](../architecture/README.md) — System design
- [Puzzle Manager CLI](puzzle-manager-cli.md) — CLI command reference
