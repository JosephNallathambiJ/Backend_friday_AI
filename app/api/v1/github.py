"""GitHub integration endpoints."""

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import verify_api_key
from app.domain.schemas import APIResponse
from app.integrations.github_client import GitHubClient

router = APIRouter(
    prefix="/api/v1/github",
    tags=["GitHub Integration"],
    dependencies=[Depends(verify_api_key)],
)


@router.get("/repos/{owner}/{repo}", response_model=APIResponse)
async def get_github_repo(owner: str, repo: str):
    client = GitHubClient()
    data = await client.get_repository(owner, repo)
    return APIResponse(data=data)


@router.get("/repos/{owner}/{repo}/issues", response_model=APIResponse)
async def list_github_issues(
    owner: str,
    repo: str,
    state: str = Query("open"),
    limit: int = Query(20, ge=1, le=100),
):
    client = GitHubClient()
    issues = await client.list_issues(owner, repo, state=state, limit=limit)
    return APIResponse(data=issues)


@router.get("/repos/{owner}/{repo}/pulls", response_model=APIResponse)
async def list_github_pulls(
    owner: str,
    repo: str,
    state: str = Query("open"),
    limit: int = Query(20, ge=1, le=100),
):
    client = GitHubClient()
    pulls = await client.list_pull_requests(owner, repo, state=state, limit=limit)
    return APIResponse(data=pulls)
