"""Git repository inspection endpoints."""

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import verify_api_key
from app.domain.schemas import APIResponse
from app.tools.git import GitDiffTool, GitStatusTool

router = APIRouter(
    prefix="/api/v1/git",
    tags=["Git Inspection"],
    dependencies=[Depends(verify_api_key)],
)


@router.get("/status", response_model=APIResponse)
async def git_status(repo_path: str | None = Query(".")):
    tool = GitStatusTool()
    result = await tool.execute({"repo_path": repo_path})
    return APIResponse(
        data=result.data,
        success=result.success,
        error={"code": "GIT_ERROR", "message": result.error} if not result.success else None,
    )


@router.get("/diff", response_model=APIResponse)
async def git_diff(
    repo_path: str | None = Query("."),
    cached: bool = Query(False),
):
    tool = GitDiffTool()
    result = await tool.execute({"repo_path": repo_path, "cached": cached})
    return APIResponse(
        data=result.data,
        success=result.success,
        error={"code": "GIT_ERROR", "message": result.error} if not result.success else None,
    )
