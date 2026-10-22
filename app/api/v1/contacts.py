"""Contacts API routes for searching and managing authorized contact records."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db
from app.domain.schemas import (
    APIResponse,
    ContactCreate,
    ContactRead,
    ContactUpdate,
)
from app.services.contacts_service import ContactsService

router = APIRouter(prefix="/contacts", tags=["Contacts"])


@router.get("", response_model=APIResponse)
async def list_or_search_contacts(
    query: str | None = Query(
        default=None, description="Search substring matching name or organization"
    ),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List or search authorized contact records."""
    if query:
        contacts = await ContactsService.search_contacts(db, query=query, limit=limit)
    else:
        contacts = await ContactsService.list_contacts(db, limit=limit, offset=offset)

    return APIResponse(
        success=True,
        data=[
            ContactRead(
                id=c.id,
                display_name=c.display_name,
                given_name=c.given_name,
                family_name=c.family_name,
                organization=c.organization,
                emails=c.emails,
                phones=c.phones,
                labels=c.labels,
                provider_id=c.provider_id,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
            for c in contacts
        ],
    )


@router.post("", response_model=APIResponse, status_code=201)
async def create_contact(
    contact_in: ContactCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new contact record."""
    contact = await ContactsService.create_contact(db, contact_in)
    return APIResponse(
        success=True,
        data=ContactRead(
            id=contact.id,
            display_name=contact.display_name,
            given_name=contact.given_name,
            family_name=contact.family_name,
            organization=contact.organization,
            emails=contact.emails,
            phones=contact.phones,
            labels=contact.labels,
            provider_id=contact.provider_id,
            created_at=contact.created_at,
            updated_at=contact.updated_at,
        ),
    )


@router.get("/{contact_id}", response_model=APIResponse)
async def get_contact(
    contact_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve details for a specific contact."""
    contact = await ContactsService.get_contact(db, contact_id)
    return APIResponse(
        success=True,
        data=ContactRead(
            id=contact.id,
            display_name=contact.display_name,
            given_name=contact.given_name,
            family_name=contact.family_name,
            organization=contact.organization,
            emails=contact.emails,
            phones=contact.phones,
            labels=contact.labels,
            provider_id=contact.provider_id,
            created_at=contact.created_at,
            updated_at=contact.updated_at,
        ),
    )


@router.patch("/{contact_id}", response_model=APIResponse)
async def update_contact(
    contact_id: str,
    updates: ContactUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update an existing contact."""
    contact = await ContactsService.update_contact(db, contact_id, updates)
    return APIResponse(
        success=True,
        data=ContactRead(
            id=contact.id,
            display_name=contact.display_name,
            given_name=contact.given_name,
            family_name=contact.family_name,
            organization=contact.organization,
            emails=contact.emails,
            phones=contact.phones,
            labels=contact.labels,
            provider_id=contact.provider_id,
            created_at=contact.created_at,
            updated_at=contact.updated_at,
        ),
    )


@router.delete("/{contact_id}", response_model=APIResponse)
async def delete_contact(
    contact_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete an authorized contact."""
    deleted = await ContactsService.delete_contact(db, contact_id)
    return APIResponse(success=True, data={"deleted": deleted, "contact_id": contact_id})
