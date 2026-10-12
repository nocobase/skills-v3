# NocoBase 3 Skills

Lightweight distribution of the global NocoBase 3 Skills maintained in [`nocobase/nocobase`, `v3-develop/skills/`](https://github.com/nocobase/nocobase/tree/v3-develop/skills). This repository does not contain the NocoBase application source. NocoBase 2 users should use [`nocobase/skills`](https://github.com/nocobase/skills).

## Install

```bash
npx skills@latest add nocobase/skills-v3 --skill '*' -g
```

Select your Coding Agent when prompted, then start a new session. To install one Skill, replace `'*'` with its name. To update, rerun the installation command, or use `npx skills@latest update` to check all tracked Skills for updates.

| Skill | Purpose |
| --- | --- |
| `nocobase-create-app` | Create and start a NocoBase 3 development application. |
| `nocobase-app-installer` | Install, upgrade, roll back and check a built application. |
| `nocobase-v3-plugin-development` | Develop plugins in a NocoBase 3 source workspace. |

The plugin development Skill is distributed as `nocobase-v3-plugin-development` to avoid overwriting the V2 `nocobase-plugin-development` Skill. Its source directory remains `skills/nocobase-plugin-development`; synchronization changes the distributed directory, frontmatter name and the UI metadata’s Skill invocation. Existing V3 installations made under the old name are not removed automatically: check which version owns that installation before removing it. If you previously installed from the application repository, rerun the new installation command to migrate to this smaller source.

## Source and synchronization

Edit Skill content in the source repository and open a PR there. Do not edit generated `skills/` files here. Relative references, scripts, assets, executable file modes and deletions are mirrored together. `.sync-source.json` records the immutable source commit and skills tree used for the current distribution.

The source repository's `v3-skills-sync.yml` sends a `skills-updated` repository dispatch when `skills/**` changes on `v3-develop`. There is no scheduled polling. This repository's `Sync NocoBase 3 Skills` workflow also supports **Actions → Sync NocoBase 3 Skills → Run workflow** for initial synchronization and recovery. It reads only the public source's skills subtree via the GitHub API and writes this repository using its own `GITHUB_TOKEN`. The source notifier uses the existing NocoBase GitHub App with contents-write access to this repository; no personal access token is stored here.

Each run reads the current `v3-develop` head and pins every file to that commit, rather than trusting a supplied event ref. Delayed events cannot roll the mirror back to an older event's commit. Unrelated source commits produce no distribution commit. A failed download or validation leaves the previous mirror published. Failed notification or synchronization is visible in the respective Actions run; enable failure notifications and use the manual entry to retry after fixing the cause.

The source workflow's paired entry on `nocobase/nocobase`'s default `main` branch dispatches its `v3-develop` implementation for manual runs. The target workflow lives on this repository's own default `main` branch. Land the source implementation before its default-branch entry, and confirm the GitHub App still has access to `skills-v3`. Maintain the distribution workflow and tests here; edit only Skill content in the source repository. Preserve the existing NocoBase 2 Skills repository.

Global Skills become public as soon as they merge into `v3-develop` and the next synchronization succeeds. A Skill describing new package commands must still wait for the corresponding npm release before its source PR merges. Synchronization does not publish packages or bypass that release rule. Application-owned Skills continue to ship in their own npm packages.

## Maintainer checks

```bash
python3 -m unittest discover -s tests -v
GH_TOKEN=... python3 scripts/sync-skills.py
```

Use a token from your environment rather than writing it into a file or shell history. Keep the managed target `skills/` free of manual content; synchronization replaces it completely. The source repository's license terms apply to the mirrored files; see [the source license](https://github.com/nocobase/nocobase/blob/v3-develop/LICENSE).
