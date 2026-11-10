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

## Second pass on Home (November 2026)

A follow-up unslop check of the live Home page found only small problems, so the look stayed the same
and just these were fixed:

| Problem | Fixed to |
|---|---|
| The merchant count said twice ("Demo (simulated 1,000 merchants) · 1,000 merchants") | Said once |
| A permanent "Light or dark: menu → Settings → Theme" note in the sidebar | Removed (this page still explains how to switch) |
| "Open the risk queue" sat higher than the Load data button, which was stretched wide | One row, lined up, button only as wide as its label |
| Uneven space around the ladder strip; a big empty band at the top and bottom | Even spacing; less padding at the top of every page |
| Feature descriptions in pale caption grey, hard to read | Normal secondary text colour |
| The sidebar hid five pages behind "View 5 more" | Every page is listed |
| Home showed counts but nothing the system actually produces | **Top of the risk queue**: the three most serious merchants, each with its shop, the main reason in plain words, and the ladder pips |

The preview uses the same live results as the Risk queue, so it changes when you load data or edit settings.
Code: `home()` in `app/dashboard.py`, `queue_preview()` in `app/ui.py`.

## Dark, soft-panel redesign (November 2026)

Modelled on an Apple-style reference screenshot: dark graphite, soft rounded corners, sections on slightly
raised grey panels, and a small search bar in the sidebar.

**What changed**

- **Dark for everyone.** The site no longer follows the viewer's computer setting; it is always dark.
  Page `#111113`, panels `#1a1a1d`, controls `#222226`, sidebar `#0b0b0d`, faint edges `#2a2a2f`.
  The greys are neutral (no blue tint), so the colour that remains means something: cobalt for the
  main button and charts, and the five ladder colours.
- **Sections sit on panels.** Each main section (a chart, a list, the analyst decision, the network picture,
  the settings form) is on a raised panel with 14px corners. Every figure (`st.metric`) is its own small card.
  Tables, expanders and notices get the same soft corners.
- **Softer corners everywhere.** Buttons and inputs 10px, cards 12px, panels 14px.
- **A new sidebar.** The Trace logo (a flat off-white mark of two linked merchants, a big one and a small one
  tied to it, for "follow the links") and name, then a **search bar**: type a page name
  ("network") to open that page, or a merchant ID ("M0002") to open its case file. Below it, every page in
  dense 32px rows with small grey section names; the open page gets a soft grey highlight.
  The menu is drawn by our own code now (`st.navigation(position="hidden")` plus `st.page_link`), which is
  what makes the search and the custom rows possible.

- **A simpler Home.** The five-box ladder strip (Monitor to Offboard) is gone from Home; the ladder still
  appears on Overview and next to every merchant. Home now shows the top of the risk queue, then
  **How Trace decides**: the three ideas side by side on one panel, numbered 01 to 03, split by faint lines.

**Where it lives**

- `.streamlit/config.toml`: the dark colours, corner sizes, fonts
- `app/ui.py`: `style()` (panels, cards, sidebar), `panel()` (wraps a section), `wordmark()`, the palettes
- `app/dashboard.py`: the sidebar (search and page list)
- Pages put sections on panels with `with ui.panel("name"):`

**Limits:** Streamlit draws some parts itself (the ⋮ menu, table headers, dropdown lists). They follow the
dark colours but can't be shaped exactly like the reference. On Streamlit Cloud, **reboot the app** after
this update, because theme settings are only read at start-up.

## Earlier dark mode (replaced by the section above)


The dashboard has a matching dark theme: deep ink surfaces (`#0b0d14`), light text, and a slightly
brighter cobalt (`#3a76c4` for buttons, `#5b93d9` in charts) so contrast stays readable. The ladder colours
have night versions too.

- **It follows the viewer's system setting automatically** (a laptop in dark mode gets the dark dashboard).
- **To switch by hand:** the ⋮ menu (top right) → **Settings** → **Theme**: Light, Dark, or Use system setting.
- Everything drawn by our own code (ladder pips, thin-bar lists, charts, network picture) looks up the
  viewer's current palette when it draws, in `app/ui.py` (`PALETTES`), so two people on different themes
  never affect each other.
- The customer's payment-screen mock-up stays light on purpose: it shows a phone app.
- On Streamlit Cloud, **reboot the app** after this update, because theme settings are only read at start-up.
