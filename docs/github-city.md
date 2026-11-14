# GitHub City: review, activation and rollback

## Design

`.github/workflows/city.yml` generates the city daily at **06:23 UTC
(03:23 America/Sao_Paulo)** and supports `workflow_dispatch`. It runs only for
`Jorge-Lana/Jorge-Lana` on `main`; there are no push or pull-request triggers.
Scheduled runs require the workflow on the default branch. GitHub can delay
schedules and disable them after inactivity in public repositories.

The read-only `generate` job runs the bundled GitWorld JavaScript, validates the
SVG, corrects its HUD label from “commits” to “contributions”, and uploads only
`city-public/gitworld.svg`. It does not install dependencies. The fresh `publish`
job verifies the file's SHA-256 against the generating job's output and repeats
SVG validation using a fresh checkout before publishing. It never runs GitWorld.

Only `publish` gets `contents: write`. Other unspecified token permissions are
disabled. The generator gets `contents: read` and checkout does not persist its
credentials. Publication uses checkout's temporary Git credentials and cleanup.
No PAT, additional secret, Pages deployment or environment setting is required.
Only GitHub's built-in `GITHUB_TOKEN` is used.

Publication creates an orphan **`city-output`** branch on first run, then adds
ordinary commits to that branch. Only `gitworld.svg` is staged. Unchanged content
creates no commit; existing other files and history are preserved. Pushes are
never forced. Network failures and rejected pushes fail the job. Concurrency
serializes city runs; neither `main` nor the Snake's `output` branch is targeted.

The public image URL is:

```text
https://raw.githubusercontent.com/Jorge-Lana/Jorge-Lana/city-output/gitworld.svg
```

This URL will not exist until the first successful publication. The README
change should therefore be activated only after the workflow has been validated.

## Reviewed upstream behavior and limitations

GitWorld is pinned to
[`76fe1d0ad8b59801e0352616cd040eece376c8cb`](https://github.com/Dasmat13/git-world-action/tree/76fe1d0ad8b59801e0352616cd040eece376c8cb).
The action definition uses Node 20 and includes `dist/index.js`, compatible with
GitHub-hosted Ubuntu runners without npm installation or compilation.

Inspection of `action.yml`, `src/index.ts`, `src/github.ts`, `src/world.ts`,
`src/renderer.ts`, `src/weather.ts` and the relevant bundled implementation found:

- The city is a 900×260 SVG with CSS/SMIL animations. Its 52 weekly columns use
  each week's **maximum daily contribution count** for height and building type.
  These are GitHub contributions, not just commits, and not individual repositories.
  The HUD total comes from the full contribution calendar returned by GitHub;
  columns use only the last 52 weeks, so it is not a sum of displayed heights.
- Stars, issues and primary languages are aggregated over at most 100 non-fork
  repositories ordered by stars, without pagination. The biome uses the most
  common primary language by repository count, not language byte totals.
- Crowns are decorative rules; PRs are not queried. No accurate PR counts or
  per-repository building mapping should be inferred. Day/night derives from
  contribution streak, not local clock time. Streak stops at the first zero day,
  including an incomplete current day.
- Token-authenticated data requests go to `api.github.com/graphql`. If the public
  profile location is nonempty, it is sent without the token to
  `geocoding-api.open-meteo.com`, then coordinates to `api.open-meteo.com`.
  Empty `location` input does not disable this. Weather errors use an
  activity-based fallback; requests have no explicit timeout, so the job has one.
- GitWorld also writes `profile-card.svg`, containing preset biography/skills
  and an issue-derived number labeled as PRs. That card is neither uploaded nor
  published; its external Google Fonts import is also excluded from the city.
- The city itself has no external assets in the reviewed renderer. The local
  validator checks the expected identity, dimensions, elements, animation and
  obvious external/active content. It is targeted validation of pinned output,
  not a general-purpose sanitizer for arbitrary hostile SVGs.

All new external `uses:` references are pinned to reviewed 40-character SHAs:

| Action | Version / SHA |
| --- | --- |
| GitWorld | `76fe1d0ad8b59801e0352616cd040eece376c8cb` |
| actions/checkout | v4.3.1 / `34e114876b0b11c390a56381ad16ebd13914f8d5` |
| actions/upload-artifact | v4.6.2 / `ea165f8d65b6e75b540449e92b4886f43607fa02` |
| actions/download-artifact | v4.3.0 / `d3f86a106a0bac45b974a628896c90dbdf5c8093` |

The download action warns rather than failing on its archive digest mismatch;
the explicit cross-job file hash check makes an SVG byte mismatch fail here.
SHA pins freeze executable code, not the runner image, GitHub/Open-Meteo services
or platform artifact storage. Review upstream changes and runtimes before updates.
No complete dependency vulnerability audit or reproducible bundle rebuild was
performed: dependencies were not installed. Upstream's README advertises MIT but
the reviewed tree has no LICENSE file. Its feature table overstates repo/PR
mapping. The existing Snake workflow's mutable action tags remain unchanged to
preserve the working fallback; they are pre-existing maintenance concerns.

## Local validation performed

No credentials or dependencies were added. Local temporary harnesses are outside
the checkout, under `/tmp/city-validation/` (not part of the integration):

```bash
python3 /tmp/city-validation/check-local.py
node /tmp/city-validation/check-browser.cjs
git diff --check
```

- The actual pinned `dist/index.js` ran with an intercepted GraphQL response and
  a dummy, non-secret token: active and zero-contribution fixtures both generated
  SVGs. Active output contained 52 weekly buildings; zero output contained none.
- The validator corrected both HUD labels, was byte-idempotent on revalidation,
  and rejected 11 unsafe/invalid variants (including script, event handler,
  external image/CSS, DTD, wrong identity, profile card, malformed/oversized XML
  and a symlink).
- Python's existing YAML parser checked configuration, permission boundaries,
  job dependencies, output paths and image URL. Pinned SHAs were compared with
  inspected action checkouts; supplied inputs matched their definitions.
  Embedded Bash passed `bash -n`. This is not a GitHub service-side validation;
  `actionlint` was unavailable and was not installed.
- The exact publication shell was exercised against a **local bare Git remote**:
  first publication, unchanged rerun and changed publication all passed. The
  changed run preserved output history/other files; `main` and Snake fixture refs
  remained unchanged. An unavailable remote aborted before branch creation.
  No real GitHub branch was pushed.
- The exact publisher verification step accepted a matching file SHA-256 and
  failed on a mismatched hash before publishing.
- Existing Chromium rendered the generated SVG; train transforms and star opacity
  changed over time. The SVG also loaded and animated when embedded as an image.
  This validates fixture rendering, not the live GitHub profile.
- The unchanged Snake workflow and README content outside the visualization
  block were compared with the original checkout. Existing `output` contains
  `github-snake.svg` and `github-snake-dark.svg`.

Live `GITHUB_TOKEN` GraphQL access, hosted job execution, artifact transfer, branch
policy, public raw URL and GitHub's image rendering/cache still require validation
after the workflow is merged. No successful GitHub Actions run is claimed.

## Review and staged activation (requires owner authorization)

No commit, push, merge or publication has been performed by this implementation.
Keep the Snake workflow and its `output` branch throughout activation.

1. Review all four changed files on `feat/github-city-profile`, including untracked
   additions. Run `git diff --check`; inspect the workflow, helper and this guide.
2. After explicitly authorizing publication, commit and push **only the workflow,
   helper and guide** first; leave `README.md` unstaged:

   ```bash
   git add .github/workflows/city.yml .github/scripts/prepare_city.py docs/github-city.md
   git commit -m "Add isolated daily GitHub City generation"
   git push -u origin feat/github-city-profile
   ```

3. Open and review a PR to `main` for those three files. The owner authorizes the
   merge. For the fast-forward sync below, use **Create a merge commit** and keep
   the feature branch. Merging enables the next scheduled run, including its
   publication to `city-output`. Leave the original README visible meanwhile.
4. In GitHub Actions, select **GitHub City → Run workflow → main**. Inspect both
   jobs and confirm success. If using an already authenticated GitHub CLI:

   ```bash
   gh workflow run city.yml --ref main
   gh run list --workflow city.yml --branch main
   gh run watch RUN_ID --exit-status
   ```

5. Check `city-output` contains the city alone on its first publication and the
   Snake branch is intact. Verify the public URL, expected account and animation:

   ```bash
   curl --fail --location --output /tmp/github-city-live.svg \
     https://raw.githubusercontent.com/Jorge-Lana/Jorge-Lana/city-output/gitworld.svg
   python3 .github/scripts/prepare_city.py /tmp/github-city-live.svg /tmp/github-city-checked.svg
   ```

   Open the raw image in a browser. Confirm the HUD says “contributions”, no
   unrelated card is displayed, and a second manual run preserves branch history.
   GitHub/raw image caching can delay visible updates. If any check fails, keep
   the README on Snake and inspect logs; do not grant extra scopes or add a PAT.
6. Only after that validation, sync the feature branch without overwriting the
   pending README, commit it and publish the second reviewed PR:

   ```bash
   git fetch origin main
   git merge --ff-only origin/main
   git add README.md
   git commit -m "Replace contribution Snake with validated GitHub City"
   git push origin feat/github-city-profile
   ```

   If the first PR was squash/rebase merged, stop at a failed fast-forward and
   reconcile history through a normal review; do not reset or force-push. The
   owner merges the README PR after review, then checks the live profile in light
   and dark modes and observes a subsequent scheduled run.

## Rollback

Disable **GitHub City** in the Actions UI to stop further publication. Restore the
previous visualization in the README with a reviewed normal commit (or revert
only the README activation commit), replacing the City section with:

```html
<!-- Contribution snake (generated by .github/workflows/snake.yml) -->
<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/Jorge-Lana/Jorge-Lana/output/github-snake-dark.svg" />
    <img alt="contribution snake" src="https://raw.githubusercontent.com/Jorge-Lana/Jorge-Lana/output/github-snake.svg" />
  </picture>
</p>
```

The original Snake workflow and assets remain available. Neither output branch
needs deletion; no history rewrite or force-push is needed. Before publication,
rollback is simply leaving these local feature-branch changes unmerged.
