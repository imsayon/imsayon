"""Run from the repository root: python3 scripts/switch_theme.py 01-editorial-card."""
from pathlib import Path
import sys
from urllib.request import urlopen


def switch(theme):
    choices = {p.stem: p for p in Path("themes").glob("[0-9][0-9]-*.md")}
    if theme not in choices:
        raise SystemExit("Unknown theme. Choose a numbered file from themes/.")
    content = choices[theme].read_text()
    if "metrics.activity.svg" in content and not Path("metrics.activity.svg").is_file():
        raise SystemExit("Generate metrics.activity.svg first. See themes/README.md; current profile unchanged.")
    if "pacman-contribution-graph" in content:
        for name in ("pacman-contribution-graph.svg", "pacman-contribution-graph-dark.svg"):
            try:
                with urlopen(f"https://raw.githubusercontent.com/imsayon/imsayon/output/{name}", timeout=20) as response:
                    if b"<svg" not in response.read():
                        raise ValueError("Missing SVG")
            except Exception as error:
                raise SystemExit("Generate Pac-Man first. See themes/README.md; current profile unchanged.") from error
    Path("README.md").write_text(content)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python3 scripts/switch_theme.py THEME")
    switch(sys.argv[1])
