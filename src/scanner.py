"""Find UPI IDs on public betting pages and match them to our merchants.

Betting sites and Telegram channels publish the UPI IDs / QR codes gamblers should pay into
("Deposit to: shree042store@okaxis"). Matching those IDs against our merchant list is the cheapest,
most certain evidence there is, and it seeds the network search.

What it understands
-------------------
* plain UPI IDs:            name@okaxis, 98xxxxxx10@ybl
* UPI payment links / QR:   upi://pay?pa=name@okaxis&pn=...&am=500
* obfuscation tricks:       "name [at] okaxis", "name (at) ybl", spaces around @
It ignores e-mail addresses (something@gmail.com) because a UPI handle never has a dot after the @.

Privacy rule (from the implementation plan): use PUBLIC pages only, record where each ID came from.
"""
from __future__ import annotations

import re
from urllib.parse import parse_qs, unquote, urlparse

import pandas as pd

# Common UPI handles (bank / app suffixes). Unknown handles are still reported, flagged as unverified.
KNOWN_HANDLES = {
    "okaxis", "oksbi", "okhdfcbank", "okicici", "ybl", "ibl", "axl", "paytm", "ptyes", "ptaxis", "pthdfc", "ptsbi",
    "apl", "yapl", "upi", "axisbank", "hdfcbank", "icici", "sbi", "kotak", "idfcbank", "indus", "federal", "fbl",
    "freecharge", "jupiteraxis", "waaxis", "wahdfcbank", "waicici", "wasbi", "aubank", "rbl", "yesbank", "barodampay",
    "pnb", "unionbank", "cnrb", "boi", "mahb", "airtel", "jio", "slice", "naviaxis", "superyes", "abfspay",
}
_DEOBF = [(re.compile(r"\s*[\[\(\{]\s*at\s*[\]\)\}]\s*", re.I), "@"), (re.compile(r"\s+@\s+"), "@")]
# a full stop is allowed right after the handle (end of a sentence) but not ".com"-style domains
_VPA = re.compile(r"(?<![\w.\-])([a-zA-Z0-9][a-zA-Z0-9.\-_]{1,255})@([a-zA-Z][a-zA-Z0-9]{1,63})(?!\w|@|\.\w)")
_LINK = re.compile(r"upi://pay\?[^\s\"'<>]+", re.I)


def extract(text: str, source: str = "pasted text") -> pd.DataFrame:
    """All UPI IDs in a piece of text, with the surrounding context."""
    raw = text
    for pat, rep in _DEOBF:
        text = pat.sub(rep, text)
    rows = []
    for m in _LINK.finditer(text):
        q = parse_qs(urlparse(m.group(0)).query)
        pa = unquote(q.get("pa", [""])[0]).strip().lower()
        if "@" in pa:
            rows.append({"upi_id": pa, "how_found": "UPI payment link / QR", "amount_in_link": q.get("am", [""])[0],
                         "payee_name_in_link": unquote(q.get("pn", [""])[0])})
    for m in _VPA.finditer(text):
        vpa = f"{m.group(1)}@{m.group(2)}".lower()
        s, e = max(0, m.start() - 40), min(len(text), m.end() + 40)
        rows.append({"upi_id": vpa, "how_found": "UPI ID in text", "context": text[s:e].replace("\n", " ")})
    if not rows:
        return pd.DataFrame(columns=["upi_id", "handle", "known_handle", "how_found", "context", "source"])
    out = pd.DataFrame(rows).drop_duplicates("upi_id", keep="first")
    out["handle"] = out.upi_id.str.split("@").str[1]
    out["known_handle"] = out.handle.isin(KNOWN_HANDLES)
    out["source"] = source
    out["obfuscated"] = raw != text
    return out.reset_index(drop=True)


def match(found: pd.DataFrame, merchants: pd.DataFrame) -> pd.DataFrame:
    """Attach our merchant_id to every extracted UPI ID we recognise."""
    if "upi_id" not in merchants or merchants.upi_id.isna().all():
        return found.assign(merchant_id=None)
    lookup = merchants.dropna(subset=["upi_id"]).assign(upi_id=lambda x: x.upi_id.astype(str).str.lower()) \
        .set_index("upi_id").merchant_id
    return found.assign(merchant_id=found.upi_id.map(lookup))


def demo_page(merchants: pd.DataFrame, known_bad_ids=(), n: int = 4) -> str:
    """A synthetic Telegram-style post advertising deposit UPI IDs (for the demo only).

    Uses merchants that are betting fronts in the simulation but NOT yet on the known-bad list, plus
    noise (an e-mail address, an unrelated UPI ID) so the extractor has something to ignore."""
    pool = merchants
    if "label" in merchants:
        pool = merchants[(merchants.label == "betting_front") & ~merchants.merchant_id.isin(set(known_bad_ids))]
    pool = pool.dropna(subset=["upi_id"]).head(n)
    v = pool.upi_id.tolist() + ["fallback001@okaxis"] * max(0, n - len(pool))
    return (
        "🏏 IPL MEGA MATCH TONIGHT 🏏  Min deposit ₹500 | Instant withdrawal\n"
        f"Deposit ID 1: {v[0]}\n"
        f"Deposit ID 2 (if ID 1 fails): {v[1].replace('@', ' [at] ')}\n"
        f"Scan & pay: upi://pay?pa={v[2]}&pn=Shree%20Traders&am=1000&cu=INR\n"
        f"Backup: {v[3]}\n"
        "Send screenshot to @BookieSupport on Telegram. Complaints: support.team@gmail.com\n"
        "Unrelated: pay your electricity bill at bescom@okhdfcbank\n"
    )
