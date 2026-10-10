# TalentLens — Visual and UX Direction

The look is a decision memo being marked up by a careful reviewer, not an HR dashboard: warm paper, ink text, and red and amber proofreading marks that carry the product's core idea.

## Avoid

These read as generic or AI-generated:

- Purple or blue gradients
- Glassmorphism
- Sparkle or robot "AI" icons
- Emoji
- Stock illustrations
- A sidebar of eight dashboard pages
- KPI tiles with no decision attached
- Rounded-everything cards with heavy shadows
- "Good morning" greetings

## Palette

| Token | Hex | Role |
|---|---|---|
| `paper` | `#FBFAF7` | Page background |
| `surface` | `#FFFFFF` | Card / panel surface |
| `ink` | `#1B1F2A` | Primary text |
| `muted-ink` | `#5B6170` | Secondary text, labels |
| `hairline` | `#E4E1DA` | Borders (instead of shadows) |
| `ledger-blue` | `#1F3A5F` | Single accent (links, active state) |
| `redline` | `#B42318` | Red constraint marks |
| `amber` | `#B54708` | Amber constraint marks |
| `green` | `#067647` | Success / approved |

All text pairs must meet WCAG AA (4.5:1 contrast ratio).

## Typography

| Use | Typeface | Notes |
|---|---|---|
| Headings | Source Serif 4 | Memo feel |
| Interface text | IBM Plex Sans | UI labels, body |
| All figures | IBM Plex Mono | Tabular numerals (`font-variant-numeric: tabular-nums`) |

Bundle fonts with `@fontsource` packages so the demo works offline. No Google Fonts CDN.

## Layout

- Top bar → workflow strip → 12-column grid
- Max width 1280 px
- Hairline borders instead of shadows
- Generous whitespace
- Big numbers paired with a one-line plain-English meaning

## Redline Marks

| Severity | Visual treatment | Text label (colour never stands alone) |
|---|---|---|
| Red | Solid double underline + small ▲ marker | "High cost" |
| Amber | Dotted underline + small ◆ marker | "Moderate cost" |

Each mark has both the visual treatment and a text label so meaning is never conveyed by colour alone.

## Skill Tags

| Source | Style | Icon |
|---|---|---|
| Assessment | Solid fill | Check icon |
| Certification | Solid fill + badge icon | Badge icon |
| Project history | Half-filled | Briefcase icon |
| Self-reported | Outlined | Person icon |

All tags readable in greyscale: shape (solid / half / outline), icon and text label carry the meaning.

## Icons

- lucide-react only
- 1.5 px stroke weight
- Used sparingly — only where a text label alone is insufficient

## Motion

- 150–200 ms transitions on state change only
- All transitions respect `prefers-reduced-motion: reduce`
- No decorative animation

## Charts

- Recharts
- Direct labels on bars
- No decorative legends
- No 3-D effects

## Copy Tone

- Business tone, short sentences
- Rupees formatted as the API returns them (₹18L)
- No exclamation marks

## Accessibility Rules (Non-Negotiable)

- WCAG 2.1 AA contrast on all text
- Visible 2 px focus ring on every interactive element
- Skip link present; landmarks: `<header>`, `<nav>`, `<main>`, `<footer>`
- Everything works by keyboard; tab order follows reading order
- Every tooltip opens by hover, keyboard focus and tap (Radix Popover for tap/click, Radix Tooltip for hover/focus, wrapped in one `InfoTip` component)
- `aria-live="polite"` live regions announce changes, e.g. "Recommendation updated: Borrow Arjun + Build Priya, ₹18L"
- No information by colour alone; charts have text equivalents
- Usable from 1280 px (demo laptop) down to 768 px; nothing breaks at 200 % zoom

## Contrast Ratios (verified)

All ratios computed with the WCAG 2.1 relative-luminance formula. WCAG AA requires ≥ 4.5:1 for normal text.

| Foreground | Background | Ratio | Pass |
|---|---|---|---|
| ink `#1B1F2A` | paper `#FBFAF7` | 15.8:1 | AA ✓ |
| ink `#1B1F2A` | surface `#FFFFFF` | 16.5:1 | AA ✓ |
| muted-ink `#5B6170` | paper `#FBFAF7` | 5.9:1 | AA ✓ |
| muted-ink `#5B6170` | surface `#FFFFFF` | 6.2:1 | AA ✓ |
| accent `#1F3A5F` | paper `#FBFAF7` | 11.0:1 | AA ✓ |
| accent `#1F3A5F` | surface `#FFFFFF` | 11.5:1 | AA ✓ |
| redline `#B42318` | paper `#FBFAF7` | 6.3:1 | AA ✓ |
| redline `#B42318` | surface `#FFFFFF` | 6.6:1 | AA ✓ |
| amber `#B54708` | paper `#FBFAF7` | 5.2:1 | AA ✓ |
| amber `#B54708` | surface `#FFFFFF` | 5.4:1 | AA ✓ |
| green `#067647` | paper `#FBFAF7` | 5.5:1 | AA ✓ |
| green `#067647` | surface `#FFFFFF` | 5.7:1 | AA ✓ |
