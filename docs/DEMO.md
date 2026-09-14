# The public pages, the figures, and which repo holds what

SEAM has three repositories. Knowing which one you are in explains where a file
belongs and why some things cannot be regenerated from this one.

| Repo | Remote | Holds |
|---|---|---|
| Working repo (private) | `Vein05/paste-boundary-inference` | Everything: dataset builders, raw run traces, paper source, audits, the export script. |
| Release repo (this one) | `aimsresearchlab/seam` | The published benchmark, scorer, per-case labels, statistics, docs. Built from the working repo by `tools/build_release.py`. |
| Lab site | `aimsresearchlab/aimsresearchlab.github.io` | The Astro site, including the interactive pages under `public/seam/` that deploy to `aimsresearchlab.com/seam/`. |

The raw model responses live only in the working repo. This repo ships the
scored labels, which is enough to reproduce every number but not to show a
model's actual text. That is why the sample bundle below is built upstream.

## The interactive pages

Two static pages, no framework, no build step:

```
public/seam/index.html          the walkthrough: one case, three seam conditions
public/seam/leaderboard.html    all 20 models, expandable per-model outputs
public/seam/icons/              brand marks (lobehub icons-static-svg)
public/seam/data/samples.json   sampled model outputs the leaderboard rows load
```

They live in the site repo under `public/`, so Astro copies them through
untouched and every path stays relative. The site is otherwise zero-JavaScript;
these pages are the documented exception (see the site repo's `CLAUDE.md`).

The walkthrough is a single GSAP timeline that measures cursor targets from the
DOM, so it reflows rather than scaling down on narrow screens, and rebuilds
itself on resize. `window.__tl` exposes the timeline, which is what makes the
figure and video captures below deterministic.

## Regenerating `samples.json`

From a working-repo checkout (needs `seam/results/*.traces.jsonl`):

```bash
python3 tools/build_demo_samples.py --out ../aims/public/seam/data/samples.json
```

It picks one composition event per source dataset, deterministically, and
exports every condition for every model that has traces, with the cascade
absorption label attached. 19 of 20 models have raw outputs; DeepSeek-V4-Flash
ships rates only, and the page says so instead of inventing text.

## Recapturing the README figures

Both figures are screenshots of the live pages, so they stay in sync with the
real thing. Serve the site (`npx astro dev` in the site repo, or any static
server over `public/`), open the page, then drive the timeline from the console
and screenshot.

`docs/img/worked-example.png`, square, 1000x1000:

```js
// on /seam/
const tl = window.__tl;
tl.pause(); tl.seek(0, false); tl.play();            // let it run to the last beat
// after ~25s of playback:
tl.pause();
document.querySelector('[data-film-cap]').style.opacity = 0;   // drop the caption pill
document.querySelector('[data-film-ctl]').style.display = 'none';
const f = document.querySelector('.frame').getBoundingClientRect();
window.scrollTo(0, f.top + window.scrollY - (1000 - f.height) / 2 - 6);
```

Capture the 1000x1000 viewport. The frame ends up centered with the prompt in
its boundary-tag state and all three verdicts visible.

`docs/img/leaderboard.png`, full width, 1600x1140:

```js
// on /seam/leaderboard.html, viewport 1600x1140
const c = document.querySelector('.card').getBoundingClientRect();
window.scrollTo(0, c.top + window.scrollY - 70);
```

Capture the viewport: all 20 rows plus the colour legend, no drawer open.

Seeking the timeline with `tl.seek(t, false)` (the `false` lets callbacks fire)
also works for stills, but step forward in small increments: captions and typed
text are written by callbacks and `onUpdate`, so a single long jump lands on a
half-written state.

## House rules that apply to these files

- No em dashes, anywhere, including page copy and code comments.
- The pages are hand-written HTML and CSS. No build step, no framework, no CDN
  fonts. GSAP is the one external script, pinned by version on cdnjs.
- Numbers on the pages come from `results/statistics.json`. Do not retype them;
  regenerate and re-embed.
