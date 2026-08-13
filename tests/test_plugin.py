"""Tests for the price_list plugin."""

import json
import re
from pathlib import Path
from unittest.mock import patch

import pytest

from plugins.price_list import PriceListPlugin
from src.plugins.base import PluginResult

MANIFEST_PATH = Path(__file__).parent.parent / "manifest.json"

COLOR_MARKER_RE = re.compile(r"\{6[3-9]\}")


def tile_len(text: str) -> int:
    """Board width in tiles: a color marker like {63} occupies one tile."""
    return len(COLOR_MARKER_RE.sub("#", text))


@pytest.fixture
def manifest_data():
    with open(MANIFEST_PATH) as f:
        return json.load(f)


def make_plugin(manifest_data, config):
    plugin = PriceListPlugin(manifest_data)
    plugin.config = {"enabled": True, **config}
    return plugin


COFFEE_ITEMS = [
    {"name": "Latte", "price": "4.50"},
    {"name": "Cappuccino", "price": "4.25"},
    {"name": "Drip Coffee", "price": "3.00"},
]


@pytest.fixture
def plugin(manifest_data):
    return make_plugin(manifest_data, {"items": list(COFFEE_ITEMS)})


class TestFetchData:
    def test_plugin_id(self, plugin):
        assert plugin.plugin_id == "price_list"

    def test_fetch_data_success(self, plugin):
        result = plugin.fetch_data()
        assert result.available is True
        assert result.error is None
        assert result.data is not None

    def test_no_items_returns_unavailable(self, manifest_data):
        plugin = make_plugin(manifest_data, {"items": []})
        result = plugin.fetch_data()
        assert result.available is False
        assert "item" in result.error.lower()

    def test_fetch_data_returns_all_declared_variables(self, plugin, manifest_data):
        result = plugin.fetch_data()
        declared = manifest_data["variables"]["simple"]
        for var in declared:
            assert var in result.data, f"Variable '{var}' declared in manifest but not in data"

    def test_items_array_matches_declared_fields(self, plugin, manifest_data):
        result = plugin.fetch_data()
        fields = manifest_data["variables"]["arrays"]["items"]["item_fields"]
        assert len(result.data["items"]) == 3
        for item in result.data["items"]:
            assert set(item.keys()) == set(fields)


class TestLineFormatting:
    def test_dot_leader_line_is_exactly_22_tiles(self, plugin):
        data = plugin.fetch_data().data
        assert data["line_1"] == "LATTE............$4.50"
        assert tile_len(data["line_1"]) == 22

    def test_spaces_style_right_aligns_price(self, manifest_data):
        plugin = make_plugin(
            manifest_data, {"items": COFFEE_ITEMS, "price_style": "spaces"}
        )
        line = plugin.fetch_data().data["line_1"]
        assert line == "LATTE            $4.50"
        assert tile_len(line) == 22

    def test_compact_style_left_aligns(self, manifest_data):
        plugin = make_plugin(
            manifest_data, {"items": COFFEE_ITEMS, "price_style": "compact"}
        )
        assert plugin.fetch_data().data["line_1"] == "LATTE $4.50"

    def test_currency_after_uses_trailing_symbol(self, manifest_data):
        plugin = make_plugin(
            manifest_data,
            {
                "items": [{"name": "Kaffe", "price": "45"}],
                "currency_symbol": "KR",
                "currency_position": "after",
            },
        )
        assert plugin.fetch_data().data["line_1"].endswith("45 KR")

    def test_blank_currency_symbol_shows_bare_price(self, manifest_data):
        plugin = make_plugin(
            manifest_data,
            {"items": [{"name": "Latte", "price": "4.50"}], "currency_symbol": ""},
        )
        assert plugin.fetch_data().data["line_1"].endswith(".4.50")

    def test_color_bullet_prepends_one_marker_tile(self, manifest_data):
        plugin = make_plugin(
            manifest_data,
            {"items": [{"name": "Latte", "price": "4.50", "color": "green"}]},
        )
        line = plugin.fetch_data().data["line_1"]
        assert line.startswith("{66} LATTE")
        assert tile_len(line) == 22

    def test_long_name_is_truncated_to_fit(self, manifest_data):
        plugin = make_plugin(
            manifest_data,
            {"items": [{"name": "Extraordinarily Long", "price": "1250.00"}]},
        )
        line = plugin.fetch_data().data["line_1"]
        assert tile_len(line) == 22
        assert line.endswith("$1250.00")
        assert ".." in line  # leaders survive truncation

    def test_names_are_uppercased(self, plugin):
        assert plugin.fetch_data().data["line_2"].startswith("CAPPUCCINO")


class TestTitle:
    def test_title_is_centered_with_accent_tiles(self, manifest_data):
        plugin = make_plugin(
            manifest_data,
            {
                "items": COFFEE_ITEMS,
                "title": "Daily Brew",
                "title_color": "yellow",
            },
        )
        data = plugin.fetch_data().data
        assert data["title"] == "DAILY BREW"
        assert data["line_1"].strip() == "{65} DAILY BREW {65}"
        # centered: content is 14 tiles, so 4 leading spaces
        assert data["line_1"].startswith("    {65}")
        assert data["line_2"] == ""  # breathing room under the title
        assert data["line_3"].startswith("LATTE")

    def test_title_without_color_has_no_markers(self, manifest_data):
        plugin = make_plugin(
            manifest_data, {"items": COFFEE_ITEMS, "title": "Menu"}
        )
        line = plugin.fetch_data().data["line_1"]
        assert "{" not in line
        assert line.strip() == "MENU"


class TestPagination:
    def eight_items(self):
        return [{"name": f"Item {i}", "price": str(i)} for i in range(1, 9)]

    def test_page_count_reflects_items_per_page(self, manifest_data):
        plugin = make_plugin(
            manifest_data, {"items": self.eight_items(), "items_per_page": 4}
        )
        data = plugin.fetch_data().data
        assert data["page_count"] == 2
        assert data["item_count"] == 8

    def test_single_page_has_empty_page_label(self, plugin):
        data = plugin.fetch_data().data
        assert data["page_count"] == 1
        assert data["page_label"] == ""

    def test_pages_rotate_with_time(self, manifest_data):
        plugin = make_plugin(
            manifest_data,
            {"items": self.eight_items(), "items_per_page": 4, "rotation_seconds": 30},
        )
        with patch("plugins.price_list.time.time", return_value=0):
            first = plugin.fetch_data().data
        with patch("plugins.price_list.time.time", return_value=30):
            second = plugin.fetch_data().data
        with patch("plugins.price_list.time.time", return_value=60):
            wrapped = plugin.fetch_data().data
        assert first["page_number"] == 1
        assert first["page_label"] == "PAGE 1/2"
        assert first["line_1"].startswith("ITEM 1")
        assert second["page_number"] == 2
        assert second["line_1"].startswith("ITEM 5")
        assert wrapped["page_number"] == 1

    def test_title_reduces_page_capacity(self, manifest_data):
        # 6 requested, but a title occupies a line -> 5 items per page
        plugin = make_plugin(
            manifest_data,
            {"items": self.eight_items(), "items_per_page": 6, "title": "Menu"},
        )
        assert plugin.fetch_data().data["page_count"] == 2


class TestFormattedDisplay:
    def test_six_plain_lines_within_22_chars(self, plugin):
        lines = plugin.get_formatted_display()
        assert lines is not None
        assert len(lines) == 6
        assert all(isinstance(line, str) and len(line) <= 22 for line in lines)
        assert all("{" not in line for line in lines)  # fallback stays marker-free

    def test_unconfigured_returns_none(self, manifest_data):
        plugin = make_plugin(manifest_data, {"items": []})
        assert plugin.get_formatted_display() is None


class TestValidateConfig:
    def test_valid_config_passes(self, plugin):
        assert plugin.validate_config(plugin.config) == []

    def test_missing_items_rejected(self, plugin):
        errors = plugin.validate_config({"items": []})
        assert any("item" in e.lower() for e in errors)

    def test_item_missing_price_rejected(self, plugin):
        errors = plugin.validate_config({"items": [{"name": "Latte"}]})
        assert any("price" in e.lower() for e in errors)

    def test_unsupported_characters_rejected(self, plugin):
        errors = plugin.validate_config(
            {"items": [{"name": "Café", "price": "4.50"}]}
        )
        assert any("caf" in e.lower() for e in errors)

    def test_invalid_color_rejected(self, plugin):
        errors = plugin.validate_config(
            {"items": [{"name": "Latte", "price": "4", "color": "magenta"}]}
        )
        assert any("color" in e.lower() for e in errors)

    def test_unsupported_currency_symbol_rejected(self, plugin):
        errors = plugin.validate_config(
            {"items": [{"name": "Latte", "price": "4"}], "currency_symbol": "€"}
        )
        assert any("currency" in e.lower() for e in errors)


class TestBoardSafety:
    def test_all_output_strings_are_board_safe(self, manifest_data):
        plugin = make_plugin(
            manifest_data,
            {
                "items": [{"name": "Latte", "price": "4.50", "color": "red"}],
                "title": "Menu & Prices",
                "title_color": "blue",
            },
        )
        data = plugin.fetch_data().data
        safe = re.compile(r"^[A-Z0-9 !@#$()\-+&=;:'\"%,./?°]*$")
        for key, value in data.items():
            if key == "items":
                values = [v for item in value for v in item.values()]
            else:
                values = [value]
            for v in values:
                stripped = COLOR_MARKER_RE.sub("", str(v))
                assert safe.match(stripped), f"{key} not board-safe: {v!r}"


class TestManifestMetadata:
    def test_manifest_uses_dict_simple_format(self, manifest_data):
        assert isinstance(manifest_data["variables"]["simple"], dict)

    def test_all_variables_have_descriptions(self, manifest_data):
        for var_name, meta in manifest_data["variables"]["simple"].items():
            assert meta.get("description"), f"Variable '{var_name}' missing description"

    def test_groups_are_defined(self, manifest_data):
        groups = manifest_data["variables"].get("groups", {})
        assert len(groups) > 0
        for group_id, group_def in groups.items():
            assert "label" in group_def, f"Group '{group_id}' missing label"

    def test_all_variables_reference_valid_groups(self, manifest_data):
        groups = set(manifest_data["variables"].get("groups", {}).keys())
        for var_name, meta in manifest_data["variables"]["simple"].items():
            group = meta.get("group", "")
            if group:
                assert group in groups, f"Variable '{var_name}' references undefined group '{group}'"

    def test_preview_rows_fit_board_width(self, manifest_data):
        widths = {"flagship": 22, "note": 15}
        for preview in manifest_data["previews"]:
            width = widths[preview["device_type"]]
            for row in preview["rows"]:
                assert tile_len(row) <= width, f"{preview['label']}: {row!r} too wide"
        assert tile_len(manifest_data["teaser"]) <= 15
