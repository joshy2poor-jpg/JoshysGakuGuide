#!/usr/bin/env python3
"""Conservative Gakuran source monitor.

It collects code-like strings only from code-marked HTML elements and from
backtick-formatted strings in active-code sections. It never declares a code
active/expired from a single source. Disagreements and newly found candidates
are marked for human review. Awakening source changes are detected and logged;
the guide is not silently rewritten from unreviewed prose.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "updates.json"
HISTORY = ROOT / "data" / "source-history.json"
HEADERS = {"User-Agent": "JoshysGakuGuideUpdater/1.0 (personal fan guide)"}
CODE_SOURCES = [
    ("RoCodes", "https://rocodes.gg/codes/gakuran"),
    ("ClaimCodes", "https://claimcodes.gg/roblox/gakuran/"),
    ("Game.Guide", "https://www.game.guide/roblox-codes/gakuran"),
]
AWAKENING_URL = "https://gakuran.cc/fighting-styles"

def now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

def fetch(url):
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return response.text

def clean_code(value):
    value = value.strip().strip("`'\"“”‘’")
    if not value or len(value) > 80:
        return None
    if not re.fullmatch(r"[A-Za-z0-9_*.-]+", value):
        return None
    # Reject common labels and reward quantities, not possible codes.
    if value.lower() in {"active", "expired", "new", "copy", "code", "codes", "rerolls", "yen"}:
        return None
    return value

def extract_active_candidates(html):
    soup = BeautifulSoup(html, "html.parser")
    page_text = soup.get_text("\n", strip=True)
    lower = page_text.lower()

    # Bound extraction to an active/working/new section when recognizable.
    starts = [x for x in (
        lower.find("active gakuran codes"),
        lower.find("all new gakuran codes"),
        lower.find("working gakuran codes"),
        lower.find("active codes"),
        lower.find("working codes"),
        lower.find("all active codes"),
    ) if x >= 0]
    if starts:
        start = min(starts)
        ends = [x for x in (
            lower.find("expired gakuran codes", start + 1),
            lower.find("expired codes", start + 1),
            lower.find("inactive codes", start + 1),
            lower.find("how do i redeem", start + 1),
            lower.find("how to redeem", start + 1),
        ) if x >= 0]
        segment = page_text[start:min(ends)] if ends else page_text[start:]
    else:
        segment = ""

    found = set()
    # Prefer code-styled elements, but only if their text also occurs in the active segment.
    if segment:
        for node in soup.find_all(["code", "kbd"]):
            value = clean_code(node.get_text(" ", strip=True))
            if value and value in segment:
                found.add(value)
        # Many code tables use inline backticks in text.
        for match in re.findall(r"`([^`]{2,80})`", segment):
            value = clean_code(match)
            if value:
                found.add(value)

    return found

def main():
    old = json.loads(DATA.read_text(encoding="utf-8")) if DATA.exists() else {}
    old_history = json.loads(HISTORY.read_text(encoding="utf-8")) if HISTORY.exists() else {}
    checked = now()
    per_source = []
    failures = []

    for name, url in CODE_SOURCES:
        try:
            html = fetch(url)
            candidates = extract_active_candidates(html)
            if not candidates:
                raise ValueError("No code candidates found in active section; page format may have changed.")
            per_source.append({"name": name, "url": url, "codes": sorted(candidates), "ok": True})
        except Exception as exc:
            failures.append(f"{name}: {type(exc).__name__}: {exc}")
            per_source.append({"name": name, "url": url, "codes": [], "ok": False, "error": str(exc)})

    # Count independent source mentions. Two or more sources = corroborated,
    # one source = unverified. No automatic expiry based on absence alone.
    counts = {}
    for item in per_source:
        if item["ok"]:
            for code in item["codes"]:
                counts.setdefault(code, []).append(item["name"])

    old_codes = {item["code"]: item for item in old.get("codes", [])}
    all_codes = sorted(set(counts) | set(old_codes), key=str.lower)
    result_codes = []
    for code in all_codes:
        sources = counts.get(code, [])
        if len(sources) >= 2:
            status = "reported_active"
        elif len(sources) == 1:
            status = "unverified"
        else:
            # Absence from a scrape is not evidence of expiry.
            status = old_codes.get(code, {}).get("status", "needs_recheck")
        result_codes.append({
            "code": code,
            "status": status,
            "sources": sources,
            "last_checked_at_utc": checked,
            "note": (
                "Listed by at least two monitored sources; still not tested in-game."
                if status == "reported_active" else
                "Only one monitored source currently lists this code; verify manually."
                if status == "unverified" else
                "Not found in current successful scans. Do not call expired without explicit source evidence."
            )
        })

    awakening = old.get("awakening_source", {})
    try:
        aw_html = fetch(AWAKENING_URL)
        aw_text = BeautifulSoup(aw_html, "html.parser").get_text("\n", strip=True)
        digest = hashlib.sha256(aw_text.encode("utf-8")).hexdigest()
        prior_digest = old_history.get("awakening_sha256")
        changed = bool(prior_digest and digest != prior_digest)
        awakening = {
            "url": AWAKENING_URL,
            "status": "changed_needs_review" if changed else "checked_no_change" if prior_digest else "baseline_saved",
            "last_checked_at_utc": checked,
            "last_changed_at_utc": checked if changed else awakening.get("last_changed_at_utc"),
            "sha256": digest,
            "note": "A source change was detected. Review the current guide before publishing changed awakening requirements."
        }
        old_history["awakening_sha256"] = digest
    except Exception as exc:
        awakening = {
            **awakening,
            "url": AWAKENING_URL,
            "status": "check_failed",
            "last_checked_at_utc": checked,
            "error": f"{type(exc).__name__}: {exc}"
        }
        failures.append(f"Awakening source: {type(exc).__name__}: {exc}")

    output = {
        "checked_at_utc": checked,
        "codes": result_codes,
        "awakening_source": awakening,
        "source_checks": per_source,
        "warnings": failures,
        "important": "Reported status is based on third-party source agreement, not live redemption in Roblox. New or changed awakening details require human review."
    }
    DATA.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    HISTORY.write_text(json.dumps(old_history, indent=2) + "\n", encoding="utf-8")
    print(f"Checked {len(per_source)} code sources; found {len(counts)} candidate codes.")
    print(f"Awakening source status: {awakening.get('status')}")
    if failures:
        print("Warnings:")
        for failure in failures:
            print(" - " + failure)

if __name__ == "__main__":
    main()
