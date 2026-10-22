"""GitHub API client with token redaction and read-only inspection."""

from typing import Any

import httpx

from app.core.config import settings
from app.core.exceptions import ProviderError, ValidationError


class GitHubClient:
    """Read-only GitHub REST API client."""

    def __init__(self, token: str | None = None):
        self.token = token or settings.GITHUB_TOKEN
        self.base_url = "https://api.github.com"

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "FRIDAY-AI-Backend",
        }
        if self.token:
            headers["Authorization"] = f"token {self.token}"
        return headers

    async def get_repository(self, owner: str, repo: str) -> dict[str, Any]:
        """Fetch repository details."""
        if not owner or not repo:
            raise ValidationError("Repository owner and repo name must not be empty.")

        url = f"{self.base_url}/repos/{owner}/{repo}"
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.get(url, headers=self._headers())
            if res.status_code == 404:
                raise ProviderError(f"GitHub repository '{owner}/{repo}' not found.")
            if res.status_code != 200:
                raise ProviderError(f"GitHub API error HTTP {res.status_code}")
            data = res.json()
            return {
                "name": data.get("name"),
                "full_name": data.get("full_name"),
                "description": data.get("description"),
                "default_branch": data.get("default_branch"),
                "stars": data.get("stargazers_count"),
                "open_issues_count": data.get("open_issues_count"),
            }

    async def list_issues(
        self, owner: str, repo: str, state: str = "open", limit: int = 20
    ) -> list[dict[str, Any]]:
        """List issues for an authorized repository."""
        url = f"{self.base_url}/repos/{owner}/{repo}/issues"
        params = {"state": state, "per_page": limit}

        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.get(url, headers=self._headers(), params=params)
            if res.status_code != 200:
                raise ProviderError(f"GitHub API returned HTTP {res.status_code}")
            items = res.json()
            return [
                {
                    "number": item.get("number"),
                    "title": item.get("title"),
                    "state": item.get("state"),
                    "created_at": item.get("created_at"),
                    "user": item.get("user", {}).get("login"),
                }
                for item in items
                if not item.get("pull_request")  # Filter out PRs from issues endpoint
            ]

    async def list_pull_requests(
        self, owner: str, repo: str, state: str = "open", limit: int = 20
    ) -> list[dict[str, Any]]:
        """List pull requests for an authorized repository."""
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls"
        params = {"state": state, "per_page": limit}

        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.get(url, headers=self._headers(), params=params)
            if res.status_code != 200:
                raise ProviderError(f"GitHub API returned HTTP {res.status_code}")
            items = res.json()
            return [
                {
                    "number": item.get("number"),
                    "title": item.get("title"),
                    "state": item.get("state"),
                    "created_at": item.get("created_at"),
                    "user": item.get("user", {}).get("login"),
                }
                for item in items
            ]
