from __future__ import annotations

import os

import httpx

from harness.tools.base import ToolResult


class WebSearchTool:
    def search(self, query: str, limit: int = 5) -> ToolResult:
        api_key = os.getenv("BRAVE_SEARCH_API_KEY")
        if not api_key:
            return ToolResult(
                tool="web_search",
                ok=True,
                summary="Search provider unavailable; returning empty fallback result",
                data={"query": query, "results": [], "degraded": True},
            )

        response = httpx.get(
            "https://api.search.brave.com/res/v1/web/search",
            params={"q": query, "count": limit},
            headers={"X-Subscription-Token": api_key, "Accept": "application/json"},
            timeout=30,
        )
        try:
            response.raise_for_status()
        except httpx.HTTPError as exc:
            return ToolResult(
                tool="web_search",
                ok=False,
                summary="Search request failed",
                data={"query": query, "error": str(exc), "results": []},
            )
        payload = response.json()
        results = payload.get("web", {}).get("results", [])
        simplified = [
            {
                "title": item.get("title"),
                "url": item.get("url"),
                "description": item.get("description"),
            }
            for item in results
        ]
        return ToolResult(
            tool="web_search",
            ok=True,
            summary=f"Found {len(simplified)} results",
            data={"query": query, "results": simplified, "degraded": False},
        )
