"""Board-geometry conformance for price_list.

Verifies the plugin renders correctly on every board shape FiestaBoard
supports -- Flagship, Note, and Note arrays (including FiestaPanel-shaped
ones) from 15x3 up to 120x24 -- using the shared conformance suite core
holds its own plugins to.

price_list is a paginated list (it rotates through pages of items), so a
taller board must show strictly more items whenever a shorter board was
already full: ``strict_growth=True``.
"""

import json
from pathlib import Path
from unittest.mock import patch

from plugins.price_list import PriceListPlugin
from src.plugins.geometry_conformance import assert_board_conformance

MANIFEST_PATH = Path(__file__).parent.parent / "manifest.json"
with open(MANIFEST_PATH) as f:
    MANIFEST = json.load(f)

# Enough items that even the tallest standard geometry (120x24, 23 items per
# page once the title's row is subtracted) never runs out of content -- the
# point is to keep every rung of the growth ladder saturated, so a plugin
# that caps its page size independently of the board shows up as a flat line
# rather than "ran out of things to say".
MANY_ITEMS = [{"name": f"Item {i}", "price": f"{i}.00"} for i in range(1, 31)]


def make_plugin() -> PriceListPlugin:
    """Fresh, ready-to-render plugin. No network involved -- pure config."""
    plugin = PriceListPlugin(MANIFEST)
    plugin.config = {
        "enabled": True,
        "title": "Daily Brew",
        "title_color": "yellow",
        "items": list(MANY_ITEMS),
        "items_per_page": 24,  # the manifest's raised cap; let the board decide
        "price_style": "dots",
    }
    return plugin


def test_renders_on_every_board_shape():
    # Page selection is driven by the wall clock (rotation_seconds), and page
    # *capacity* differs per geometry, so different boards can land on
    # different page indices at real time.time() -- including a final,
    # partially-filled page on one geometry and a full page on another. That
    # is a real feature (rotation), not a geometry bug, so it is pinned out
    # here: time.time() == 0 makes _current_page() resolve to page 0 on every
    # geometry, and MANY_ITEMS is large enough that page 0 is always full.
    with patch("plugins.price_list.time.time", return_value=0):
        assert_board_conformance(
            make_plugin,
            manifest=MANIFEST,
            strict_growth=True,
            require_note_array_preview=True,
        )
