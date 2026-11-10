# 17. The design pass (unslop)

The dashboard and landing page were redesigned with **unslop**, a design checklist by Damir
Sokolovsky (@heydamir, CC BY 4.0, https://github.com/heydamir/unslop). It targets the tell-tale signs of
AI-built interfaces and replaces them with deliberate choices.

## What it found

| Sign of "AI-made" design | Where | Fixed to |
|---|---|---|
| Emoji as icons (🏠 📊 🕸️ …) | All 16 menu items, case statuses, payment screen | One line-icon set; plain status text with a small status dot |
| Heavy bold headings, default font | Every page | IBM Plex Sans at weight 500; IBM Plex Mono for figures |
| Brightly coloured pill badges | Every action label | "Ladder pips" (below) |
| Nine equal stat boxes, one duplicate, one filler | Overview | Four stats that each say something different |
| Rainbow bar chart on an uneven log scale | Overview | A weekly trend line plus a ranked list with thin bars |
| Every filter chip highlighted | Risk queue, Case management | A quiet three-way switch |
| Mixed number formats (89.19% next to 100%) | Overview | One format |
| Developer "Deploy" toolbar | Top of every page | Hidden |
| Uppercase tracked label, weight-700 headline, no product visual | Landing page | Sentence case, lighter headline, a real product preview |

## The direction

- **Product:** a risk console that tells a payment provider's compliance team which UPI merchants' money
  doesn't match their declared business, and what to do about each.
- **Character:** exact, fair, unhurried.
- **World:** a bank's compliance desk, so cool ink-grey neutrals and one cobalt accent (`#1f5fae`).
- **Moment:** on each merchant's page, a chart showing how far the merchant is from similar shops on every
  signal, with plain comparisons ("57% vs 10% for peers").
- **Signature:** **ladder pips**, five small steps showing where a merchant sits from Monitor to Offboard,
  used everywhere an action appears (sidebar logo on the landing page, badges, lists).

## Where it lives

- `.streamlit/config.toml`: colours, fonts, weights, corner radius, chart colours
- `app/ui.py`: chart theme, ladder colours, the pips, thin-bar lists, line icons
- `site/index.html`: the landing page

Colours still carry meaning only: grey (Monitor), cobalt (Ask), amber (Friction), ember (Review), dark red (Offboard).
