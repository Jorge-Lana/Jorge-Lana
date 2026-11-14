# GitHub City: review, activation and rollback

## Current state

Phase 1 was committed as `9ad01cca275b983510927cfab81e003663a49b81`, pushed to
`feat/github-city-profile`, and submitted for independent review in
[PR #1](https://github.com/Jorge-Lana/Jorge-Lana/pull/1). The review corrections
update that same PR. The local Phase 2 README edit remains uncommitted and is
excluded from Phase 1. The Snake workflow and its `output` branch remain intact.
No successful GitHub-hosted City run has been observed. Phase 1 is not fully
validated until the real workflow passes; merging and Phase 2 need owner approval.

## Architecture and permissions

`.github/workflows/city.yml` runs daily at **06:23 UTC (03:23 America/Sao_Paulo)**
and via `workflow_dispatch`, only for `Jorge-Lana/Jorge-Lana` on `main`. There are
no push/PR triggers. Schedules require the default branch; GitHub may delay runs
or disable schedules after public-repository inactivity.

The generator uses the explicit username `Jorge-Lana`, runs the bundled GitWorld
code with `contents: read`, and does not persist checkout credentials. It validates
the city, changes the HUD label from “commits” to “contributions”, and uploads only
`city-public/gitworld.svg`. The separate upstream profile card is excluded.

A fresh publisher gets `contents: write`, verifies the file SHA-256 against the
generating job's output, and independently validates the SVG using a fresh
checkout. It never executes GitWorld. Unspecified token permissions are disabled.
Only the built-in `GITHUB_TOKEN` is used; no PAT, new secret or dependency install
is required. Checkout removes its temporary publication credentials on cleanup.

Publication creates an orphan `city-output` branch on first run, then ordinary
commits that stage only `gitworld.svg`. Existing history/other files are preserved;
identical output creates no commit. Concurrency serializes runs. Pushes are never
forced, and network/authentication/push errors fail the job. Neither `main` nor
Snake's `output` branch is a publication target.

The public URL becomes available after the first successful publication:

```text
https://raw.githubusercontent.com/Jorge-Lana/Jorge-Lana/city-output/gitworld.svg
```

## Node.js 24 and reviewed Action pins

| Action | Release | Immutable SHA | Declared runtime |
| --- | --- | --- | --- |
| actions/checkout | v6.1.0 | `d23441a48e516b6c34aea4fa41551a30e30af803` | node24 |
| actions/upload-artifact | v7.0.2 | `cf430e030ddbb5b0abf93d22962f4752f3646cd9` | node24 |
| actions/download-artifact | v8.0.2 | `9000827ccba6bdab643e8b6fd33ac0654aef8333` | node24 |
| Dasmat13/git-world-action | reviewed commit | `76fe1d0ad8b59801e0352616cd040eece376c8cb` | node20 metadata; Node 24 locally exercised |

Official release tags, action definitions, supplied inputs and bundled entrypoints
were inspected. Node 24 needs runner >=2.327.1; checkout's >=2.329.0 requirement
for authenticated Git inside Docker actions does not apply to this workflow.
Checkout v6 stores credentials under `RUNNER_TEMP`, linked by Git-directory config;
the publisher's branch switch preserves that directory and authentication route.

Upload v7 defaults to `archive: true`; download v8 defaults to decompression and
extracts the named artifact directly into the target directory. Both use
`@actions/artifact ^6.3.1`. The single-file archive/name/path contract is preserved.
Download now defaults to `digest-mismatch: error`; the independent SVG SHA-256
check remains an additional boundary.

The unchanged pinned GitWorld bundle was actually executed on **Node v24.22.1**,
not merely syntax-checked. Mocked active, zero-contribution and location/weather
responses all produced valid city SVGs, including CSS/SMIL animation. No fork or
upstream code edit was necessary. Its metadata still declares `node20`: the real
hosted runner's Node 24 runtime selection, authentication and artifact services
remain unverified until the post-merge run. Do not interpret local simulations
as GitHub-hosted success. The supplied Node 20 retirement changelog URL returned
HTTP 403 in this environment, so local runtime/source evidence is reported here.

## SVG validation boundary

`prepare_city.py` uses only the Python standard library. After XML parsing, it
checks **decoded attribute values and style text**, including numeric XML
references. It accepts the pinned SVG namespace, reviewed element/attribute sets,
900×260 dimensions, expected identity, CSS keyframes and SMIL `animateMotion`.

It rejects DTD/entities, processing instructions, unsupported elements/attributes,
event handlers, namespaced attributes (including `xml:base` and `xlink:href`),
CSS escapes, unsupported CSS functions/at-rules and external resource references.
CSS comments are removed before checking; `url(...)` must be complete and point
to an existing internal SVG ID. Neither external CSS imports nor external images
are supported. The label correction is byte-idempotent; other drawing bytes and
legitimate animation are preserved.

This is targeted validation of reviewed, pinned GitWorld output, **not a generic
SVG sanitizer** or a security proof for arbitrary CSS/browser behavior. Renderer
updates need review and tests; unexpected syntax fails closed. It does not audit
all upstream JavaScript/dependencies. The generator remains isolated from write
credentials even if its output is invalid.

## Verified upstream limitations

- The city has 52 weekly columns; height/type use each week's maximum daily
  GitHub contribution count, not individual repositories or commits. The HUD
  total comes from the full returned calendar, not a sum of displayed heights.
- Stars/issues and languages cover at most 100 non-fork repositories ordered by
  stars, without pagination. The biome counts primary languages by repository,
  not language bytes. Crowns are decorative; no PR query exists.
- Day/night derives from streak, not local clock time. Streak stops on the first
  zero day, including an incomplete current day.
- Token-authenticated requests go to `api.github.com/graphql`. If public profile
  location is nonempty, Open-Meteo receives that city string and then coordinates,
  without the token. Empty `location` input does not disable weather. Errors fall
  back to activity-derived weather; job timeouts limit requests without deadlines.
- The excluded profile card contains preset biography/skills, issue-derived “PR”
  statistics and an external Google Fonts import.
- No full dependency audit or reproducible bundle rebuild was performed. Upstream
  advertises MIT but the reviewed tree has no LICENSE file. Existing mutable
  Snake Action references remain unchanged as the working fallback. Pins and
  runtime compatibility require future maintenance/review.

## Local validation

Committed regression tests and the pinned zero-contribution SVG fixture run
without network or new dependencies:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s .github/scripts/tests -v
git diff --check
```

All 11 regression tests and the additional local checks below passed during the
review correction. No tests were skipped.

The tests cover valid pinned output and animation, idempotence, malformed XML,
disallowed elements/events, external resources, numeric XML references in CSS,
escapes/comments/functions/URLs, namespaces/PIs, identity/dimensions/profile-card
rejection, DTD, size and symlink handling. The numeric-reference CSS regression
was reproduced against the old validator (accepted) and the correction (rejected).

Additional local checks: Python AST syntax; workflow YAML, Bash syntax, SHA pins,
runtime/input declarations and permissions; Node 24 bundle execution with active,
zero and weather fixtures; validation of those full generated SVGs; Chromium
rendering and animation as an embedded image. The original temporary harness also
exercises publication against a local bare remote, including initial/no-op/update
runs, preservation and failure paths. None of these contact GitHub's artifact
service or publish a live SVG. `actionlint` was unavailable and not installed.

## Owner-approved merge and two-phase activation

1. Independently review and approve existing **PR #1**. Do not merge merely
   because local checks pass. Keep the feature branch and Snake intact. The
   owner can merge Phase 1 when satisfied; this enables future scheduled City
   generation/publication while the public README still shows Snake.
2. After merge, run **Actions → GitHub City → Run workflow → main**. Confirm
   Node 24 execution, both jobs, token permissions, artifact transfer/hash and
   publication to `city-output`. With an already authenticated CLI:

   ```bash
   gh workflow run city.yml --ref main
   gh run list --workflow city.yml --branch main
   gh run watch RUN_ID --exit-status
   ```

3. Verify the public image, correct account, contribution label and animation;
   confirm Snake artifacts remain intact and a second run preserves history:

   ```bash
   curl --fail --location --output /tmp/github-city-live.svg \
     https://raw.githubusercontent.com/Jorge-Lana/Jorge-Lana/city-output/gitworld.svg
   python3 .github/scripts/prepare_city.py /tmp/github-city-live.svg /tmp/github-city-checked.svg
   ```

   If these checks fail, keep the README on Snake and inspect logs; do not add
   a PAT or grant extra scopes. Raw/GitHub image caching can delay visible updates.
4. Only after a real successful run and SVG validation, review and authorize the
   separate **Phase 2 README activation PR**. Preserve the pending local edit when
   syncing history. If Phase 1 used a merge commit, a normal fast-forward sync is
   possible; if it was squash/rebase merged, reconcile without reset/force-push.
   Then commit/push only the reviewed README activation, have its PR approved,
   and check the live profile in light/dark modes and a subsequent scheduled run.

## Rollback

Before merge, leave PR #1 unmerged; the public profile and Snake are unaffected.
After an approved merge, disable **GitHub City** in Actions to stop publication
and revert Phase 1 through normal reviewed commits if needed. Never delete output
branches or rewrite history. If Phase 2 is activated later, revert only its README
activation commit to restore the existing light/dark Snake URLs under `output`.
The Snake workflow and its assets remain available throughout.
