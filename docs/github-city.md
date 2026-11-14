# GitHub City: night renderer and safe publication

## Current state and approach

The original workflow was merged in [PR #1](https://github.com/Jorge-Lana/Jorge-Lana/pull/1)
and the README activation in [PR #2](https://github.com/Jorge-Lana/Jorge-Lana/pull/2).
The owner reports successful hosted generation/publication; the public flat SVG
was independently fetched and validated. This upgrade has local browser/test
evidence, not an observed GitHub-hosted run. It needs independent PR approval.

The upgrade replaces the drawing, not the data collector: pinned GitWorld still
runs first. The local Python renderer projects its validated weekly activity into
a self-contained 1200×720 dark isometric SVG. Roofs, shaded sides, depth ordering,
shadows, windows, streets, rail/traffic and a subdued skyline/fog add depth.
No new dependency, API call, external asset, service or secret is introduced.

## What the README supports

[GitHub sanitizes rendered HTML](https://github.com/github/markup#github-markup).
[SVG used as an image](https://developer.mozilla.org/en-US/docs/Web/SVG/Guides/SVG_as_an_image)
cannot run JavaScript or load external resources. The tested README-style image
also does not forward pointer hover to inner SVG elements. Consequently:

- CSS/SMIL animation supplies moving transit, layered mist and slow light changes.
- Native `prefers-reduced-motion: reduce` hides moving transit/fog and stops lights.
- An ordinary outer README link opens the same script-free SVG at full size.
- No inline WebGL, Three.js, orbit controls, internal clicks or hover are claimed.

A separate interactive website would require another application and publication
path. It is unnecessary for the preferred in-profile result and is not added.
The full-size view is an animated image, not an interactive 3D application.

## Honest data mapping

The upstream renderer's 52 weekly positions use the **maximum daily GitHub
contribution count in each week**, logarithmically normalized against the greatest
daily count in the displayed period. Its rounded building height is:

```text
flat_height = round(10 + 130 × log(weekly_peak + 1) / log(global_peak + 1))
dark_height = 25 + 150 × (flat_height - 10) / 130
```

`render_city.py` reads the first body rectangle of each indexed `g.col` from the
validated, pinned flat output. It rejects malformed/duplicate indices and heights;
missing indices denote zero weeks under this specific renderer contract. There
are 52 lots, arranged in four chronological rows of 13, oldest to newest. Nonzero
weeks have towers; zero weeks have low park geometry. The input is normalized
intensity, **not recoverable exact weekly counts**, commits alone or repositories.

The correct “contributions” HUD total is retained from GitHub's full returned
calendar. It need not equal any sum of the displayed heights or last 52 weeks.
The distant skyline, rail, traffic, lighting and atmosphere are decorative, not
extra contribution buildings or PR/repository metrics. Deterministic geometry
ensures identical data produces identical SVG bytes; animation runs at view time.

Upstream still queries up to 100 non-fork repositories for its own flat fallback
stats and may send the public profile location/coordinates to Open-Meteo without
the token. The dark renderer uses neither those repository stats nor weather;
it makes no network requests. Upstream's preset profile card remains excluded.

## Workflow, fallback and permissions

`.github/workflows/city.yml` keeps the daily **06:23 UTC / 03:23 São Paulo** schedule,
manual dispatch, explicit `Jorge-Lana` target, and repository/`main` guard. There
are no push or PR triggers. Workflow permissions default to `{}`.

1. The generator gets `contents: read`; checkout does not persist credentials.
2. Pinned GitWorld emits the original flat SVG; `prepare_city.py` validates it and
   corrects the HUD wording to “contributions”. Invalid upstream output aborts.
3. The local renderer attempts the dark drawing and its output is validated.
   **Any renderer or dark-validation failure selects the validated flat SVG**, emits
   a workflow warning, and keeps the original publication working. It never uses
   a partial or unvalidated dark artifact.
4. The canonical single-file artifact remains `city-public/gitworld.svg`; its
   SHA-256 is passed separately to the fresh publisher.
5. Only the publisher gets `contents: write`. It runs no GitWorld/renderer code,
   checks the downloaded hash and independently validates either approved SVG
   profile. Ordinary commits stage only `gitworld.svg` on `city-output`, preserving
   other files/history. No force-push; unchanged content creates no commit.

The same public URL works before and after upgrade, so the README never points
to a nonexistent replacement asset:

```text
https://raw.githubusercontent.com/Jorge-Lana/Jorge-Lana/city-output/gitworld.svg
```

The output branch currently contains just `gitworld.svg`; the existing flat
version remains in branch history. Snake's separate `output` branch is untouched.
Concurrency still serializes city runs. Failures in upstream generation, transfer,
hash verification or publication fail closed and leave the last public image.

## Action pins and runtime

| Action | Release | Immutable SHA |
| --- | --- | --- |
| checkout | v6.1.0 | `d23441a48e516b6c34aea4fa41551a30e30af803` |
| upload-artifact | v7.0.2 | `cf430e030ddbb5b0abf93d22962f4752f3646cd9` |
| download-artifact | v8.0.2 | `9000827ccba6bdab643e8b6fd33ac0654aef8333` |
| GitWorld | reviewed commit | `76fe1d0ad8b59801e0352616cd040eece376c8cb` |

All official Actions declare Node 24; GitWorld's metadata remains `node20`, with
its actual bundle previously exercised locally on Node v24.22.1. The Python
renderer uses only the standard library available on `ubuntu-latest`.
Upload's zipped archive and download's extraction/name/path contract are unchanged;
download fails on archive digest mismatch, with the existing file hash check
retained. No PAT, new secret, Pages deployment or setting change is required.

## Validation boundary and local checks

`prepare_city.py` retains the strict 900×260 legacy profile and accepts the new
profile only with `data-theme="dark-isometric-v1"` and exact 1200×720 dimensions.
New drawing elements/attributes are restricted to the dark profile. Checks run
on decoded XML attributes/style text, reject scripts, event handlers, external
resources, namespaced attributes, DTD/PIs and CSS escapes, and restrict URLs to
existing internal IDs. Only the exact reduced-motion query is additionally allowed.
This is validation of two reviewed renderer formats, not a generic SVG sanitizer.

Run the committed tests without installing dependencies:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s .github/scripts/tests -v
python3 .github/scripts/prepare_city.py INPUT_FLAT.svg /tmp/flat-checked.svg
python3 .github/scripts/render_city.py /tmp/flat-checked.svg /tmp/night.svg
python3 .github/scripts/prepare_city.py /tmp/night.svg /tmp/night-checked.svg
git diff --check
```

Tests cover both validators, decoded-reference security regressions, deterministic
zero/sparse/full activity, exactly 52 lots, input bounds, CLI output, and the real
renderer-to-publisher validation contract, including the maximum-output size.
Full activity remains below the 1 MiB publication limit.

Local temporary harnesses also exercised the exact generation shell: renderer
failure/invalid dark output select byte-identical validated flat output with the
correct hash; invalid flat aborts. The success path, YAML/Bash syntax, permission
boundaries, immutable pins, canonical path and normal publication history are
checked locally. `actionlint` is unavailable and was not installed.

Chromium checks confirmed direct and image-embedded animation, full/zero activity
rendering, no horizontal overflow at a 320px viewport, and static image frames
with Chromium's native reduced-motion preference. A controlled test separately
confirmed scripts/hover do not activate inside an SVG image, but outer click-through
works. These are local checks, not proof of GitHub's cache, runner or live profile.

## Review, hosted validation and rollback

No merge is performed by this task. After independent approval and owner merge:

1. Dispatch `city.yml` on `main`, inspect both jobs and ensure the log says
   `Validated dark city selected.` A successful run with a fallback warning is
   preserved availability, **not successful dark-renderer activation**.
2. Fetch the public URL, check the dark marker/dimensions, correct HUD and 52 lots,
   then validate it with `prepare_city.py`. Check light/dark GitHub themes, narrow
   and wide profile layouts, full-size link and reduced-motion behavior.
3. Observe a subsequent scheduled run. GitHub may delay/cache image changes or
   disable inactive public schedules. Sparse contribution history intentionally
   yields mostly parks; the map is illustrative, not a camera-controlled scene.

On a transient dark-renderer failure, automatic flat fallback needs no intervention.
To roll back the upgrade permanently, revert the upgrade commit through a normal
reviewed PR and dispatch the restored workflow; it republishes the original flat
city to the same URL. Until then, the last published image remains visible.
No output history needs deletion or rewriting. For a further rollback to Snake,
revert the README activation or restore its existing light/dark URLs on `output`;
its workflow/assets have been preserved throughout.

Remaining upstream limits: no complete dependency audit/reproducible bundle rebuild;
upstream advertises MIT without a LICENSE file in the reviewed tree. Pins/runtime
updates require renewed review. The original Snake's mutable Action tags remain
pre-existing maintenance work outside this upgrade.
