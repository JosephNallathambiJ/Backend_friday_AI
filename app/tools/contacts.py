"""Contacts tools for searching, creating, and managing permitted contact records."""

import time
from typing import Any

from pydantic import BaseModel, Field

from app.db.session import async_session_factory
from app.domain.enums import CapabilityType, ToolRiskLevel
from app.domain.schemas import ContactCreate
from app.services.contacts_service import ContactsService
from app.tools.base import BaseTool, ToolResult


class SearchContactsInput(BaseModel):
    query: str = Field(description="Search term matching name or organization")
    limit: int = Field(default=20, description="Max results to return")


class CreateContactInput(BaseModel):
    display_name: str = Field(description="Full display name of contact")
    given_name: str | None = Field(default=None, description="Given name")
    family_name: str | None = Field(default=None, description="Family name")
    organization: str | None = Field(default=None, description="Company / Organization")
    emails: list[str] = Field(default_factory=list, description="Email addresses")
    phones: list[str] = Field(default_factory=list, description="Phone numbers")
    labels: list[str] = Field(default_factory=list, description="Tags / Labels")


class DeleteContactInput(BaseModel):
    contact_id: str = Field(description="ID of contact to delete")


class SearchContactsTool(BaseTool):
    name = "search_contacts"
    description = "Search authorized device contacts by name or organization."
    input_schema = SearchContactsInput
    required_capabilities = [CapabilityType.CONTACTS_READ.value]
    risk_level = ToolRiskLevel.READ_ONLY
    requires_approval = False

    def check_availability(self) -> dict[str, Any]:
        return ContactsService.check_availability()

    async def execute(self, parameters: dict[str, Any], dry_run: bool = False) -> ToolResult:
        t0 = time.time()
        try:
            avail = self.check_availability()
            if not avail["available"]:
                return ToolResult(
                    success=False,
                    error=f"Capability unavailable: {avail['reason']}",
                    verified=False,
                    verification_details="Provider not configured.",
                )

            params = self.validate_parameters(parameters)
            async with async_session_factory() as db:
                contacts = await ContactsService.search_contacts(
                    db, query=params["query"], limit=params.get("limit", 20)
                )
                data = [
                    {
                        "id": c.id,
                        "display_name": c.display_name,
                        "organization": c.organization,
                        "emails": c.emails,
                        "phones": c.phones,
                    }
                    for c in contacts
                ]
            return ToolResult(
                success=True,
                data={"contacts": data, "count": len(data)},
                execution_time_ms=int((time.time() - t0) * 1000),
                verified=True,
                verification_details=f"Retrieved {len(data)} contacts from authorized provider.",
            )
        except Exception as e:
            return ToolResult(
                success=False, error=str(e), execution_time_ms=int((time.time() - t0) * 1000)
            )


class CreateContactTool(BaseTool):
    name = "create_contact"
    description = "Add a new contact to authorized contacts storage."
    input_schema = CreateContactInput
    required_capabilities = [CapabilityType.CONTACTS_WRITE.value]
    risk_level = ToolRiskLevel.LOCAL_MUTATION
    requires_approval = False
    supports_dry_run = True

    def check_availability(self) -> dict[str, Any]:
        return ContactsService.check_availability()

    async def execute(self, parameters: dict[str, Any], dry_run: bool = False) -> ToolResult:
        t0 = time.time()
        try:
            avail = self.check_availability()
            if not avail["available"] and not dry_run:
                return ToolResult(
                    success=False,
                    error=f"Capability unavailable: {avail['reason']}",
                    verified=False,
                    verification_details="Provider not configured.",
                )

            params = self.validate_parameters(parameters)
            if dry_run:
                return ToolResult(
                    success=True,
                    data={"dry_run": True, "display_name": params["display_name"]},
                    dry_run=True,
                )

            contact_in = ContactCreate(
                display_name=params["display_name"],
                given_name=params.get("given_name"),
                family_name=params.get("family_name"),
                organization=params.get("organization"),
                emails=params.get("emails", []),
                phones=params.get("phones", []),
                labels=params.get("labels", []),
            )
            async with async_session_factory() as db:
                contact = await ContactsService.create_contact(db, contact_in)
                res = {
                    "id": contact.id,
                    "display_name": contact.display_name,
                    "organization": contact.organization,
                }
            return ToolResult(
                success=True,
                data=res,
                execution_time_ms=int((time.time() - t0) * 1000),
                verified=True,
                resource_references=[f"contact:{contact.id}"],
                verification_details=f"Verified contact '{contact.display_name}' persisted with ID {contact.id}.",
            )
        except Exception as e:
            return ToolResult(
                success=False, error=str(e), execution_time_ms=int((time.time() - t0) * 1000)
            )


class DeleteContactTool(BaseTool):
    name = "delete_contact"
    description = "Delete an authorized contact record."
    input_schema = DeleteContactInput
    required_capabilities = [CapabilityType.CONTACTS_WRITE.value]
    risk_level = ToolRiskLevel.DESTRUCTIVE
    requires_approval = True
    supports_dry_run = True

    def check_availability(self) -> dict[str, Any]:
        return ContactsService.check_availability()

    async def execute(self, parameters: dict[str, Any], dry_run: bool = False) -> ToolResult:
        t0 = time.time()
        try:
            avail = self.check_availability()
            if not avail["available"] and not dry_run:
                return ToolResult(
                    success=False,
                    error=f"Capability unavailable: {avail['reason']}",
                    verified=False,
                    verification_details="Provider not configured.",
                )

            params = self.validate_parameters(parameters)
            contact_id = params["contact_id"]
            if dry_run:
                return ToolResult(
                    success=True, data={"dry_run": True, "contact_id": contact_id}, dry_run=True
                )

            async with async_session_factory() as db:
                deleted = await ContactsService.delete_contact(db, contact_id)
            return ToolResult(
                success=True,
                data={"deleted": deleted, "contact_id": contact_id},
                execution_time_ms=int((time.time() - t0) * 1000),
                verified=True,
                resource_references=[f"contact:{contact_id}"],
                verification_details=f"Verified contact '{contact_id}' deleted from database.",
            )
        except Exception as e:
            return ToolResult(
                success=False, error=str(e), execution_time_ms=int((time.time() - t0) * 1000)
            )
