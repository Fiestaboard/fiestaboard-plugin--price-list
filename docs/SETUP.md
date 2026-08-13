# Price List Setup Guide

Display a styled price list or menu sign with your own items, prices, and colors, plus automatic page rotation for longer menus.

## Overview

**What it does:** Turns your board into a pricing sign for a coffee shop, restaurant, bar, or any small business. You enter the items and prices in the plugin settings, style the sign (title, colors, line style, currency), and the board displays it — rotating through pages automatically if the list is longer than one screen.

**Prerequisites:** None. Everything comes from the plugin settings — no API keys or accounts.

## Quick Setup

1. **Enable** — On the Integrations page, find **Price List** and toggle it on.
2. **Configure** — Open the plugin settings:
   - Add your **Items**: one row per product, each with a name (e.g. `Latte`) and a price (e.g. `4.50` — just the amount; the currency symbol is added for you). Optionally pick a **color bullet** to highlight an item.
   - Optionally set a **Sign Title** (e.g. `DAILY BREW`) and a **Title Accent Color**.
   - Pick your **Currency Symbol** and whether it goes before (`$4.50`) or after (`4.50 KR`) the price.
   - Pick a **Line Style**: `dots` (`LATTE....$4.50`), `spaces` (right-aligned price), or `compact` (`LATTE $4.50`).
   - If you have more items than fit on one screen, set **Page Rotation** to how long each page should show.
3. **Template** — Create a page using the plugin's demo template, or add the line variables yourself:
   ```
   {{price_list.line_1}}
   {{price_list.line_2}}
   {{price_list.line_3}}
   {{price_list.line_4}}
   {{price_list.line_5}}
   {{price_list.line_6}}
   ```
4. **View** — Set the page live. The sign renders immediately and rotates pages on its own.

## Template Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `{{price_list.line_1}}` … `{{price_list.line_6}}` | The current page, fully formatted (auto-rotating) | `LATTE...........$4.50` |
| `{{price_list.title}}` | The configured sign title | `DAILY BREW` |
| `{{price_list.page_label}}` | `PAGE X/Y`, empty when everything fits on one page | `PAGE 1/2` |
| `{{price_list.page_number}}` / `{{price_list.page_count}}` | Current page / total pages | `1` / `2` |
| `{{price_list.item_count}}` | Total configured items | `8` |
| `{{price_list.items.N.name}}` | Item N's name (0-based) | `LATTE` |
| `{{price_list.items.N.price}}` | Item N's raw price text | `4.50` |
| `{{price_list.items.N.price_display}}` | Item N's price with currency | `$4.50` |
| `{{price_list.items.N.formatted}}` | Item N as a full formatted line | `LATTE............$4.50` |
| `{{price_list.items.N.color_tile}}` | Item N's color tile marker | `{66}` |

## Configuration Reference

| Setting | Type | Required | Default | Description |
|---------|------|----------|---------|-------------|
| `enabled` | boolean | No | false | Enable/disable the plugin |
| `title` | string | No | (blank) | Heading shown at the top of every page; blank for none |
| `title_color` | string | No | none | Accent tile color beside the title |
| `items` | array | **Yes** | — | Products to show: `name`, `price`, optional `color` |
| `currency_symbol` | string | No | `$` | Added to every price; blank for none |
| `currency_position` | string | No | before | `before` (`$4.50`) or `after` (`4.50 KR`) |
| `price_style` | string | No | dots | `dots`, `spaces`, or `compact` |
| `items_per_page` | integer | No | 5 | Max items on screen at once (1–6) |
| `rotation_seconds` | integer | No | 30 | Seconds each page shows before rotating |

No environment variables are used.

## Troubleshooting

**"No items configured" error** — The plugin needs at least one item with both a name and a price. Check that no item row is empty.

**Characters missing or an "unsupported characters" error** — The split-flap board only renders letters, digits, and basic punctuation. Currency signs like `€` or `£` can't be displayed; use the currency symbol setting with text like `EUR`, `GBP`, or `KR` (and position `after`) instead. Accented letters (é, ñ) also can't render — spell items with plain letters.

**Pages don't rotate exactly on time** — The board refreshes on its own schedule (typically every 15 seconds), so a page switch lands on the next refresh after the rotation interval elapses. Use a `rotation_seconds` of 30+ for predictable behavior.

**Names look cut off** — A line is 22 tiles wide. A color bullet uses 2 tiles and the price uses its own width, so very long names are truncated to fit. Shorten the name or drop the color bullet.

**Title missing on some pages** — The title shows on every page, but it occupies one of the 6 lines, so with a title at most 5 items fit per page regardless of the Items Per Page setting.
