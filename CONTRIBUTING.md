# Contributing

Collaboration is graded from the Git history (20 % of the grade). Every member must have
meaningful commits **from their own GitHub account** in every phase.

## One-time setup

1. Accept the GitHub invitation to the repository.
2. Make sure your commits are linked to your account (otherwise they do not count):
   ```bash
   git config --global user.name  "Your Name"
   git config --global user.email "the-email-registered-in-your-github-account"
   ```
   Check at https://github.com/settings/emails. After your first push, your avatar must appear next to the commit on GitHub.
3. Follow the setup in [README §8](README.md#8-reproducing-the-project).

## Workflow (every task)

```bash
git checkout main && git pull
git checkout -b <name>/<short-task>            # e.g. julio/census-profiling
# ... work, then commit in small logical steps ...
git add <files>
git commit -m "feat(census): clean AGEB-level census table"
git push -u origin <name>/<short-task>
gh pr create --fill                             # or open the PR on github.com
```

- One branch and one PR per task. `main` is protected: direct pushes are rejected and every PR needs **1 approval** from another member.
- **CI** (GitHub Actions) runs on every PR: Python lint + every module must import, and `01_schema.sql` + `03_views.sql` must run on PostGIS. Fix red checks before asking for review.
- Someone else reviews and merges with **"Create a merge commit"** (never "Squash and merge": it would collapse your commits into one).
- Small commits with clear messages. No "final upload" commits.
- Never commit `data/raw/`, `data/processed/`, `.env` or `.venv/`.
- Before opening a PR: `python -m src.pipeline all` must run without errors.

## Commit message convention

`<type>(<area>): <what>` — types: `feat`, `fix`, `docs`, `sql`, `analysis`, `refactor`, `test`, `chore`.
Areas: `geo`, `census`, `denue`, `crime`, `dw`, `kpi`, `spatial`, `report`, `repo`.
