import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from switch_theme import switch

original = Path.cwd()
with TemporaryDirectory() as directory:
    try:
        os.chdir(directory)
        Path("themes").mkdir()
        Path("themes/01-editorial-card.md").write_text("# Sayon\n")
        Path("themes/03-activity-pulse.md").write_text("metrics.activity.svg")
        Path("themes/04-pacman-graph.md").write_text("pacman-contribution-graph")
        switch("01-editorial-card")
        assert Path("README.md").read_text() == "# Sayon\n"
        for theme in ("../README", "03-activity-pulse", "04-pacman-graph"):
            with patch("switch_theme.urlopen", side_effect=OSError("offline")):
                try:
                    switch(theme)
                except SystemExit:
                    pass
                else:
                    raise AssertionError("Invalid or unready theme was accepted")
            assert Path("README.md").read_text() == "# Sayon\n"
        Path("metrics.activity.svg").write_text("<svg/>")
        switch("03-activity-pulse")
        assert Path("README.md").read_text() == "metrics.activity.svg"
    finally:
        os.chdir(original)
print("PASS: theme switching and failure preservation")
