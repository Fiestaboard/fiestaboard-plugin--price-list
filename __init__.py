"""Price List plugin for FiestaBoard.

Display a styled price list or menu sign with your own items, prices, and
colors, plus automatic page rotation for longer menus.
"""

import logging
import math
import re
import time
from typing import Any, Dict, List, Optional

from src.plugins.base import PluginBase, PluginResult

logger = logging.getLogger(__name__)

BOARD_COLS = 22
BOARD_ROWS = 6

COLOR_MARKERS = {
    "red": "{63}",
    "orange": "{64}",
    "yellow": "{65}",
    "green": "{66}",
    "blue": "{67}",
    "violet": "{68}",
    "white": "{69}",
}

# Characters the split-flap board can physically render (see src/board_chars.py).
SAFE_CHARS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 !@#$()-+&=;:'\"%,./?°")

COLOR_MARKER_RE = re.compile(r"\{6[3-9]\}")

MIN_LEADER = 2  # dots/spaces always separating name from price


def _tile_len(text: str) -> int:
    """Width in board tiles: a color marker like {63} occupies one tile."""
    return len(COLOR_MARKER_RE.sub("#", text))


def _board_safe(text: str) -> bool:
    return all(ch in SAFE_CHARS for ch in text.upper())


class PriceListPlugin(PluginBase):
    """Config-driven price sign with per-item colors and page rotation.

    All content comes from settings (no network). When items span multiple
    pages, the current page is derived from the wall clock so the sign
    rotates on every board refresh tick.
    """

    @property
    def plugin_id(self) -> str:
        return "price_list"

    # -- rendering -----------------------------------------------------

    def _price_display(self, price: str) -> str:
        symbol = self.config.get("currency_symbol", "$").strip().upper()
        price = price.strip().upper()
        if not symbol:
            return price
        if self.config.get("currency_position", "before") == "after":
            return f"{price} {symbol}"
        return f"{symbol}{price}"

    def _item_line(self, item: Dict[str, Any], with_color: bool = True) -> str:
        """One board line for an item, exactly BOARD_COLS tiles wide.

        (Except compact style, which is left-aligned and only as wide as
        its content.)
        """
        prefix = ""
        color = item.get("color", "none")
        if with_color and color in COLOR_MARKERS:
            prefix = COLOR_MARKERS[color] + " "
        width = BOARD_COLS - _tile_len(prefix)

        name = item.get("name", "").strip().upper()
        price = self._price_display(item.get("price", ""))
        style = self.config.get("price_style", "dots")

        if style == "compact":
            return (prefix + f"{name} {price}")[: len(prefix) + width]

        max_name = width - len(price) - MIN_LEADER
        name = name[:max_name]
        leader = ("." if style == "dots" else " ") * (width - len(name) - len(price))
        return f"{prefix}{name}{leader}{price}"

    def _title_line(self, with_color: bool = True) -> str:
        title = self.config.get("title", "").strip().upper()
        marker = COLOR_MARKERS.get(self.config.get("title_color", "none"))
        content = f"{marker} {title} {marker}" if (marker and with_color) else title
        pad = max(0, (BOARD_COLS - _tile_len(content)) // 2)
        return " " * pad + content

    def _page_lines(self, page_items: List[Dict[str, Any]], with_color: bool = True) -> List[str]:
        lines = []
        if self.config.get("title", "").strip():
            lines.append(self._title_line(with_color))
            if len(page_items) + 2 <= BOARD_ROWS:
                lines.append("")  # breathing room under the title
        lines.extend(self._item_line(item, with_color) for item in page_items)
        lines = lines[:BOARD_ROWS]
        while len(lines) < BOARD_ROWS:
            lines.append("")
        return lines

    # -- pagination ----------------------------------------------------

    def _page_capacity(self) -> int:
        rows_for_items = BOARD_ROWS - (1 if self.config.get("title", "").strip() else 0)
        return min(int(self.config.get("items_per_page", 5) or 5), rows_for_items)

    def _current_page(self, page_count: int) -> int:
        if page_count <= 1:
            return 0
        rotation = max(1, int(self.config.get("rotation_seconds", 30) or 30))
        return int(time.time() // rotation) % page_count

    # -- plugin contract -----------------------------------------------

    def fetch_data(self) -> PluginResult:
        try:
            items = self.config.get("items") or []
            if not items:
                return PluginResult(
                    available=False,
                    error="No items configured - add at least one item with a name and price",
                )

            capacity = self._page_capacity()
            page_count = math.ceil(len(items) / capacity)
            page_index = self._current_page(page_count)
            page_items = items[page_index * capacity : (page_index + 1) * capacity]
            lines = self._page_lines(page_items)

            data: Dict[str, Any] = {
                "title": self.config.get("title", "").strip().upper(),
                "page_number": page_index + 1,
                "page_count": page_count,
                "page_label": f"PAGE {page_index + 1}/{page_count}" if page_count > 1 else "",
                "item_count": len(items),
                "items": [
                    {
                        "name": item.get("name", "").strip().upper(),
                        "price": item.get("price", "").strip().upper(),
                        "price_display": self._price_display(item.get("price", "")),
                        "formatted": self._item_line(item),
                        "color_tile": COLOR_MARKERS.get(item.get("color", "none"), ""),
                    }
                    for item in items
                ],
            }
            for i, line in enumerate(lines, start=1):
                data[f"line_{i}"] = line

            return PluginResult(available=True, data=data)
        except Exception as e:  # fetch_data must never raise -- surface as unavailable
            logger.exception("Error computing price_list data")
            return PluginResult(available=False, error=str(e))

    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        errors = []

        items = config.get("items") or []
        if not items:
            errors.append("Add at least one item with a name and price")

        for i, item in enumerate(items, start=1):
            name = (item.get("name") or "").strip()
            price = (item.get("price") or "").strip()
            if not name:
                errors.append(f"Item {i} needs a name")
            elif not _board_safe(name):
                errors.append(
                    f"Item name '{name}' uses characters the board can't display - "
                    "stick to letters, numbers, and basic punctuation"
                )
            if not price:
                errors.append(f"Item {i} ('{name or '?'}') needs a price")
            elif not _board_safe(price):
                errors.append(
                    f"Price '{price}' uses characters the board can't display - "
                    "stick to letters, numbers, and basic punctuation"
                )
            color = item.get("color", "none")
            if color not in ("none", *COLOR_MARKERS):
                errors.append(
                    f"Item {i} color '{color}' is not valid - choose one of: "
                    "none, " + ", ".join(COLOR_MARKERS)
                )

        symbol = config.get("currency_symbol", "$")
        if symbol and not _board_safe(symbol):
            errors.append(
                f"Currency symbol '{symbol}' can't be shown on the board - "
                "use board-safe text like $, USD, or KR"
            )

        title = config.get("title", "")
        if title and not _board_safe(title):
            errors.append(
                f"Title '{title}' uses characters the board can't display - "
                "stick to letters, numbers, and basic punctuation"
            )
        title_color = config.get("title_color", "none")
        if title_color not in ("none", *COLOR_MARKERS):
            errors.append(
                f"Title color '{title_color}' is not valid - choose one of: "
                "none, " + ", ".join(COLOR_MARKERS)
            )

        return errors

    def get_formatted_display(self) -> Optional[List[str]]:
        """Fallback rendering: the current page, without color tiles."""
        items = self.config.get("items") or []
        if not items:
            return None
        capacity = self._page_capacity()
        page_count = math.ceil(len(items) / capacity)
        page_index = self._current_page(page_count)
        page_items = items[page_index * capacity : (page_index + 1) * capacity]
        return [line[:BOARD_COLS] for line in self._page_lines(page_items, with_color=False)]


# Export hook: the loader looks for a module-level `Plugin`.
Plugin = PriceListPlugin
