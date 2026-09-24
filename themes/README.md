# Profile themes

Editorial Card is the default. Only the root `README.md` appears on the profile; these are saved alternatives.

## Change the theme on GitHub

1. Open [Switch profile theme](https://github.com/imsayon/imsayon/actions/workflows/switch-theme.yml).
2. Click **Run workflow**, leave the branch as **main**, and select a theme.
3. Click **Run workflow** again. A successful run commits the chosen README to main.

Switch back with `01-editorial-card`. Selecting the current theme makes no commit.

Edit a theme's numbered Markdown file here to customize it, then run the switcher. Switching replaces the root README; save any direct root edits into its theme file first. Previous versions remain in Git history.

## Available themes

| Theme | Preview | Requirements |
| --- | --- | --- |
| `01-editorial-card` | [Editorial Card](01-editorial-card.md) | Ready |
| `02-typewriter-intro` | [Typewriter Intro](02-typewriter-intro.md) | Included SVG |
| `03-activity-pulse` | [Activity Pulse](03-activity-pulse.md) | Generate image first |
| `04-pacman-graph` | [Pac-Man Graph](04-pacman-graph.md) | Generate image first |
| `05-monospace-cv` | [Monospace CV](05-monospace-cv.md) | Ready |
| `06-editorial-magazine` | [Editorial Magazine](06-editorial-magazine.md) | Ready |
| `07-blueprint-schematic` | [Blueprint Schematic](07-blueprint-schematic.md) | Included SVG |
| `08-swiss-grid` | [Swiss Grid](08-swiss-grid.md) | Included SVG |
| `09-editorial-terminal` | [Editorial + Terminal](09-editorial-terminal.md) | Ready |
| `10-editorial-pulse` | [Editorial + Activity Pulse](10-editorial-pulse.md) | Generate image first |
| `11-terminal-blueprint` | [Terminal + Blueprint](11-terminal-blueprint.md) | Included SVG |
| `12-engineering-arcade` | [Engineering + Quiet Arcade](12-engineering-arcade.md) | Generate image first |

## Generated themes: one-time setup

**Pac-Man (04, 12):** copy [setup/pacman.yml](setup/pacman.yml) to `.github/workflows/pacman.yml` on main. Run **Generate Pac-Man** once. It generates both light/dark images on the `output` branch with the repository token. Then select the theme. The output branch is managed by that workflow; keep unrelated files elsewhere.

**Activity Pulse (03, 10):** copy [setup/metrics.yml](setup/metrics.yml) to `.github/workflows/metrics.yml`. Add an Actions secret named `METRICS_TOKEN`, then run **Activity Pulse** once. Its successful run commits `metrics.activity.svg` to main. Then select the theme.

The metrics traffic plugin requires a classic token with `repo` scope, which can access private repositories. Activity is restricted to public events, but traffic/line totals may include accessible private repositories. To avoid that scope, set `plugin_traffic: no` and use a scopeless classic token for public activity/lines. Never paste tokens into a file.

The switcher refuses missing generated images, keeping the current profile unchanged. SVG headers are already included and require no setup. Theme previews for generated designs show images only after generation.

## Local switching

From a clone of this repository:

```bash
python3 scripts/switch_theme.py 01-editorial-card
```

Review, commit, and push the changed README. Run the small switcher check with `python3 scripts/test_switch_theme.py`.

Designs adapted from [Awesome GitHub Profile](https://github.com/beydemirfurkan/awesome-github-profile), with license in `TEMPLATE-LICENSE.txt`. Workflow action references follow the supplied upstream templates and can change over time.
