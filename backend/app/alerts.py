"""Failure alerts — open a deduped GitHub issue after N consecutive failures for a
source, turning silent breakage into a discrete fix prompt (the hands-off model).
Best-effort: the caller guarantees an alert failure never crashes the poller.
"""

from __future__ import annotations

import httpx

from app.config import settings

LABEL = "source-failure"
_API = "https://api.github.com"


async def open_issue_if_needed(
    client: httpx.AsyncClient, source: str, failures: int, error: str
) -> None:
    if failures < settings.failure_alert_threshold or not settings.github_token:
        return

    headers = {
        "Authorization": f"Bearer {settings.github_token}",
        "Accept": "application/vnd.github+json",
    }
    title = f"[source-failure] {source} is failing"

    existing = await client.get(
        f"{_API}/repos/{settings.github_repo}/issues",
        params={"labels": LABEL, "state": "open"},
        headers=headers,
        timeout=20.0,
    )
    if existing.status_code == 200 and any(i.get("title") == title for i in existing.json()):
        return  # already open — don't spam

    body = (
        f"Source `{source}` has failed {failures} consecutive polls.\n\n"
        f"Last error:\n```\n{error}\n```\n\n_Filed automatically by fly-safe._"
    )
    await client.post(
        f"{_API}/repos/{settings.github_repo}/issues",
        json={"title": title, "body": body, "labels": [LABEL]},
        headers=headers,
        timeout=20.0,
    )
