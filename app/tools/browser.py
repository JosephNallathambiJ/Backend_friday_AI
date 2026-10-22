"""Browser and Web Research tools for FRIDAY AI."""

import time
from typing import Any

from pydantic import BaseModel, Field

from app.domain.enums import CapabilityType, ToolRiskLevel
from app.services.browser_service import BrowserAutomationService
from app.services.web_research_service import WebResearchService
from app.tools.base import BaseTool, ToolResult


# --- Input Schemas ---
class WebSearchInput(BaseModel):
    query: str = Field(description="Search terms to look up on the web")
    max_results: int = Field(default=5, description="Maximum number of search results to retrieve")


class FetchWebpageInput(BaseModel):
    url: str = Field(description="Public HTTP/HTTPS URL of the webpage to fetch")


class BrowserNavigateInput(BaseModel):
    url: str = Field(description="Public URL to open in isolated browser")
    session_id: str = Field(default="default", description="Browser session identifier")


class BrowserReadInput(BaseModel):
    session_id: str = Field(default="default", description="Browser session identifier")


class BrowserInteractInput(BaseModel):
    action: str = Field(description="Interaction action: click, fill, select")
    selector: str = Field(description="CSS selector targeting the DOM element")
    value: str | None = Field(default=None, description="Text value to enter or option to select")
    session_id: str = Field(default="default", description="Browser session identifier")


class BrowserCloseInput(BaseModel):
    session_id: str = Field(default="default", description="Browser session identifier to close")


# --- Tool Classes ---
class WebSearchTool(BaseTool):
    name = "web_search"
    description = "Search public web sources for up-to-date information."
    input_schema = WebSearchInput
    required_capabilities = [CapabilityType.NETWORK_FETCH.value]
    risk_level = ToolRiskLevel.NETWORK_ACCESS
    requires_approval = False

    async def execute(self, parameters: dict[str, Any], dry_run: bool = False) -> ToolResult:
        t0 = time.time()
        try:
            params = self.validate_parameters(parameters)
            if dry_run:
                return ToolResult(
                    success=True, data={"dry_run": True, "query": params["query"]}, dry_run=True
                )

            results = await WebResearchService.search(
                query=params["query"],
                max_results=params.get("max_results", 5),
            )
            return ToolResult(
                success=True,
                data={"results": results, "count": len(results)},
                execution_time_ms=int((time.time() - t0) * 1000),
                verified=True,
                verification_details=f"Retrieved {len(results)} search results from public web.",
            )
        except Exception as e:
            return ToolResult(
                success=False, error=str(e), execution_time_ms=int((time.time() - t0) * 1000)
            )


class FetchWebpageTool(BaseTool):
    name = "fetch_webpage"
    description = (
        "Safely retrieve and extract text and links from a public webpage with SSRF protection."
    )
    input_schema = FetchWebpageInput
    required_capabilities = [CapabilityType.NETWORK_FETCH.value]
    risk_level = ToolRiskLevel.NETWORK_ACCESS
    requires_approval = False

    async def execute(self, parameters: dict[str, Any], dry_run: bool = False) -> ToolResult:
        t0 = time.time()
        try:
            params = self.validate_parameters(parameters)
            if dry_run:
                return ToolResult(
                    success=True, data={"dry_run": True, "url": params["url"]}, dry_run=True
                )

            data = await WebResearchService.fetch_webpage(url=params["url"])
            return ToolResult(
                success=True,
                data=data,
                execution_time_ms=int((time.time() - t0) * 1000),
                verified=True,
                resource_references=[params["url"]],
                verification_details=f"Preserved URL '{params['url']}', extracted {len(data.get('text', ''))} characters.",
            )
        except Exception as e:
            return ToolResult(
                success=False, error=str(e), execution_time_ms=int((time.time() - t0) * 1000)
            )

    def validate_result(self, result: ToolResult, parameters: dict[str, Any]) -> ToolResult:
        if result.success and result.data:
            url = parameters.get("url")
            if not result.resource_references and url:
                result.resource_references = [url]
            text_len = len(result.data.get("text", ""))
            if text_len == 0 and not result.dry_run:
                result.verified = False
                result.error = "Fetched page returned empty content."
            else:
                result.verified = True
        return result


class BrowserNavigateTool(BaseTool):
    name = "browser_navigate"
    description = "Open and navigate to a URL using an isolated browser session."
    input_schema = BrowserNavigateInput
    required_capabilities = [CapabilityType.BROWSER_NAVIGATE.value]
    risk_level = ToolRiskLevel.NETWORK_ACCESS
    requires_approval = False

    def check_availability(self) -> dict[str, Any]:
        return BrowserAutomationService.check_availability()

    async def execute(self, parameters: dict[str, Any], dry_run: bool = False) -> ToolResult:
        t0 = time.time()
        try:
            avail = self.check_availability()
            if not avail["available"] and not dry_run:
                return ToolResult(
                    success=False,
                    error=f"Capability unavailable: {avail['reason']}",
                    verified=False,
                    verification_details="Browser automation not configured.",
                )

            params = self.validate_parameters(parameters)
            if dry_run:
                return ToolResult(
                    success=True, data={"dry_run": True, "url": params["url"]}, dry_run=True
                )

            res = await BrowserAutomationService.open_url(
                url=params["url"],
                session_id=params.get("session_id", "default"),
            )
            return ToolResult(
                success=True,
                data=res,
                execution_time_ms=int((time.time() - t0) * 1000),
                verified=True,
                resource_references=[res.get("url", params["url"])],
                verification_details=f"Navigated to {res.get('url')} with status {res.get('status')}.",
            )
        except Exception as e:
            return ToolResult(
                success=False, error=str(e), execution_time_ms=int((time.time() - t0) * 1000)
            )


class BrowserReadTool(BaseTool):
    name = "browser_read"
    description = "Extract visible page text and links from the current browser session."
    input_schema = BrowserReadInput
    required_capabilities = [CapabilityType.BROWSER_READ.value]
    risk_level = ToolRiskLevel.READ_ONLY
    requires_approval = False

    def check_availability(self) -> dict[str, Any]:
        return BrowserAutomationService.check_availability()

    async def execute(self, parameters: dict[str, Any], dry_run: bool = False) -> ToolResult:
        t0 = time.time()
        try:
            avail = self.check_availability()
            if not avail["available"]:
                return ToolResult(
                    success=False,
                    error=f"Capability unavailable: {avail['reason']}",
                    verified=False,
                    verification_details="Browser automation not configured.",
                )

            params = self.validate_parameters(parameters)
            res = await BrowserAutomationService.read_page_content(
                session_id=params.get("session_id", "default")
            )
            return ToolResult(
                success=True,
                data=res,
                execution_time_ms=int((time.time() - t0) * 1000),
                verified=True,
                verification_details=f"Extracted {len(res.get('text', ''))} chars from browser session.",
            )
        except Exception as e:
            return ToolResult(
                success=False, error=str(e), execution_time_ms=int((time.time() - t0) * 1000)
            )


class BrowserInteractTool(BaseTool):
    name = "browser_interact"
    description = "Interact with a DOM element (click, fill form, select dropdown) in the browser."
    input_schema = BrowserInteractInput
    required_capabilities = [CapabilityType.BROWSER_INTERACT.value]
    risk_level = ToolRiskLevel.LOCAL_MUTATION
    requires_approval = False

    def check_availability(self) -> dict[str, Any]:
        return BrowserAutomationService.check_availability()

    async def execute(self, parameters: dict[str, Any], dry_run: bool = False) -> ToolResult:
        t0 = time.time()
        try:
            avail = self.check_availability()
            if not avail["available"] and not dry_run:
                return ToolResult(
                    success=False,
                    error=f"Capability unavailable: {avail['reason']}",
                    verified=False,
                    verification_details="Browser automation not configured.",
                )

            params = self.validate_parameters(parameters)
            if dry_run:
                return ToolResult(
                    success=True, data={"dry_run": True, "action": params["action"]}, dry_run=True
                )

            res = await BrowserAutomationService.interact(
                action=params["action"],
                selector=params["selector"],
                value=params.get("value"),
                session_id=params.get("session_id", "default"),
            )
            return ToolResult(
                success=True,
                data=res,
                execution_time_ms=int((time.time() - t0) * 1000),
                verified=True,
                verification_details=f"DOM interaction '{params['action']}' completed on '{params['selector']}'.",
            )
        except Exception as e:
            return ToolResult(
                success=False, error=str(e), execution_time_ms=int((time.time() - t0) * 1000)
            )


class BrowserCloseTool(BaseTool):
    name = "browser_close"
    description = "Close an active browser session and cleanup memory."
    input_schema = BrowserCloseInput
    required_capabilities = [CapabilityType.BROWSER_NAVIGATE.value]
    risk_level = ToolRiskLevel.READ_ONLY
    requires_approval = False

    def check_availability(self) -> dict[str, Any]:
        return BrowserAutomationService.check_availability()

    async def execute(self, parameters: dict[str, Any], dry_run: bool = False) -> ToolResult:
        t0 = time.time()
        try:
            params = self.validate_parameters(parameters)
            closed = await BrowserAutomationService.close_session(
                session_id=params.get("session_id", "default")
            )
            return ToolResult(
                success=True,
                data={"closed": closed},
                execution_time_ms=int((time.time() - t0) * 1000),
                verified=True,
                verification_details="Browser session context cleanly closed.",
            )
        except Exception as e:
            return ToolResult(
                success=False, error=str(e), execution_time_ms=int((time.time() - t0) * 1000)
            )

