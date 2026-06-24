# -*- coding: utf-8 -*-
"""
GitHub-backed sent-story history for the Westbury Intelligence newsletter.

Railway containers are ephemeral, so we can't keep history on local disk.
Instead we read/write a JSON file (`sent_history.json`) directly in the repo
via the GitHub Contents API. Each entry records a story we already emailed,
so the next run can exclude it (story-level dedup).

IMPORTANT: the GITHUB_TOKEN must be a fine-grained PAT with
"Contents: Read and write" on the repo. A read-only token passes the GET load
but every save fails 403 ("Resource not accessible by personal access token"),
which silently kills dedup and makes the newsletter repeat itself.
"""

import os
import re
import json
import base64
import requests

GITHUB_REPO = os.getenv("GITHUB_REPO", "aryansinha-16/westbury_newsletter")
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "master")
HISTORY_PATH = "sent_history.json"
RETENTION_DAYS = 10

_API = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{HISTORY_PATH}"


def _headers():
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        return None
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def normalize_headline(title: str) -> str:
    """Loose key so the same story from different outlets collapses together."""
    title = title.lower()
    title = re.sub(r"[^a-z0-9 ]", " ", title)
    words = [w for w in title.split() if len(w) > 3]
    return " ".join(sorted(set(words)))


def load_history() -> tuple[list, str | None]:
    """Return (entries, file_sha). entries = [{date, title, url, key, company}]."""
    headers = _headers()
    if not headers:
        print("  [history] GITHUB_TOKEN not set — running without dedup memory.")
        return [], None
    try:
        resp = requests.get(_API, headers=headers, params={"ref": GITHUB_BRANCH}, timeout=15)
        if resp.status_code == 404:
            return [], None
        resp.raise_for_status()
        data = resp.json()
        content = base64.b64decode(data["content"]).decode("utf-8")
        entries = json.loads(content) if content.strip() else []
        return entries, data["sha"]
    except Exception as e:
        print(f"  [history] load failed ({e}) — running without dedup memory.")
        return [], None


def recent_titles(entries: list, today_iso: str, days: int = RETENTION_DAYS) -> list[str]:
    """Headlines from the last `days` days, for the model's exclusion list."""
    cutoff = _shift_iso(today_iso, -days)
    return [e["title"] for e in entries if e.get("date", "") >= cutoff]


def last_story_per_company(entries: list, companies: list[str]) -> dict[str, dict]:
    """Most recent story we sent for each company → {company: {date, title}}.

    Matches a story to a company by name appearing in the title, or by the
    entry's stored `company` field. Used to show 'last major news: ...' next
    to a company that has nothing new today.
    """
    # If entries carry explicit company tags, trust them exclusively — fuzzy
    # title matching causes cross-company bleed.
    any_tagged = any(e.get("company") for e in entries)

    result: dict[str, dict] = {}
    for company in companies:
        needle = company.lower().replace(" india", "").replace(" group", "").strip()
        best = None
        for e in entries:
            if any_tagged:
                if e.get("company", "").lower() != company.lower():
                    continue
            else:
                if not (needle and needle in e.get("title", "").lower()):
                    continue
            if best is None or e.get("date", "") >= best.get("date", ""):
                best = e
        if best:
            result[company] = {"date": best["date"], "title": best["title"]}
    return result


def sent_keys(entries: list) -> set[str]:
    return {e.get("key", "") for e in entries if e.get("key")}


def _match_company(title: str, companies: list[str]) -> str:
    """Best-guess company for a story title, or '' if none matches."""
    low = title.lower()
    for company in companies:
        needle = company.lower().replace(" india", "").replace(" group", "").strip()
        if needle and needle in low:
            return company
    return ""


def save_history(entries: list, new_stories: list[dict], sha: str | None,
                 today_iso: str, companies: list[str] | None = None) -> None:
    """Append new_stories, prune > RETENTION_DAYS old, write back to GitHub."""
    headers = _headers()
    if not headers:
        return

    companies = companies or []
    seen = sent_keys(entries)
    for s in new_stories:
        key = normalize_headline(s["title"])
        if key and key not in seen:
            entries.append({
                "date": today_iso,
                "title": s["title"],
                "url": s["url"],
                "key": key,
                "company": _match_company(s["title"], companies),
            })
            seen.add(key)

    cutoff = _shift_iso(today_iso, -RETENTION_DAYS)
    entries = [e for e in entries if e.get("date", "") >= cutoff]

    body = {
        "message": f"Update sent_history for {today_iso}",
        "content": base64.b64encode(json.dumps(entries, indent=2).encode("utf-8")).decode("ascii"),
        "branch": GITHUB_BRANCH,
    }
    if sha:
        body["sha"] = sha
    try:
        resp = requests.put(_API, headers=headers, json=body, timeout=15)
        resp.raise_for_status()
        print(f"  [history] saved {len(new_stories)} new stories ({len(entries)} retained).")
    except Exception as e:
        print(f"  [history] save failed: {e}")


def _shift_iso(iso_date: str, delta_days: int) -> str:
    """Shift a YYYY-MM-DD string by delta_days, no datetime.now() needed."""
    from datetime import date, timedelta
    y, m, d = (int(x) for x in iso_date.split("-"))
    return (date(y, m, d) + timedelta(days=delta_days)).isoformat()
