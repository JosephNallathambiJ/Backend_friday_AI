"""Tool discovery and manual execution endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, verify_api_key
from app.domain.schemas import APIResponse, ToolExecuteRequest, ToolRead
from app.tools.registry import tool_registry

router = APIRouter(
    prefix="/api/v1/tools",
    tags=["Tools & Capabilities"],
    dependencies=[Depends(verify_api_key)],
)


@router.get("", response_model=APIResponse)
async def list_tools():
    """List all registered tools, their schemas, risk classifications, and approval rules."""
    from pydantic import BaseModel

    tools = tool_registry.list_tools()
    items = []
    for t in tools:
        if isinstance(t.input_schema, type) and issubclass(t.input_schema, BaseModel):
            schema = t.input_schema.model_json_schema()
        elif isinstance(t.input_schema, dict):
            schema = t.input_schema
        else:
            schema = getattr(t, "parameters_schema", {})

        items.append(
            ToolRead(
                name=t.name,
                description=t.description,
                risk_level=t.risk_level,
                requires_approval=t.requires_approval,
                required_capabilities=t.required_capabilities,
                parameters_schema=schema,
            )
        )
    return APIResponse(data=items)


@router.get("/diagnostics", response_model=APIResponse)
async def diagnose_tools():
    """Return live capability status, availability, and provider configuration for all tools."""
    diagnostics = tool_registry.diagnose_all_tools()
    return APIResponse(data={"total": len(diagnostics), "tools": diagnostics})


@router.post("/execute", response_model=APIResponse)
async def execute_tool(
    payload: ToolExecuteRequest,
    db: AsyncSession = Depends(get_db),
):
    """Execute a tool directly or run a dry-run check. Requires approval_id if tool requires approval."""
    result = await tool_registry.execute_tool(
        name=payload.tool_name,
        parameters=payload.parameters,
        session=db,
        approval_id=payload.approval_id,
        dry_run=payload.dry_run,
    )
    return APIResponse(data=result.model_dump())
