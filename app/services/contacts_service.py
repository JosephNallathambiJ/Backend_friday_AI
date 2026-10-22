"""Contacts service with provider abstraction, search, and privacy minimization."""

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.db.models.contact import ContactRecord
from app.domain.schemas import ContactCreate, ContactUpdate


class ContactsService:
    """Manages contact records with search, filtering, and provider support."""

    @staticmethod
    async def list_contacts(
        db: AsyncSession, limit: int = 50, offset: int = 0
    ) -> list[ContactRecord]:
        """List contacts with pagination."""
        stmt = (
            select(ContactRecord).order_by(ContactRecord.display_name).offset(offset).limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def search_contacts(db: AsyncSession, query: str, limit: int = 20) -> list[ContactRecord]:
        """Search contacts by display name or organization."""
        pattern = f"%{query}%"
        stmt = (
            select(ContactRecord)
            .where(
                or_(
                    ContactRecord.display_name.ilike(pattern),
                    ContactRecord.organization.ilike(pattern),
                )
            )
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_contact(db: AsyncSession, contact_id: str) -> ContactRecord:
        """Retrieve a specific contact record."""
        stmt = select(ContactRecord).where(ContactRecord.id == contact_id)
        contact = (await db.execute(stmt)).scalars().first()
        if not contact:
            raise NotFoundError(f"Contact '{contact_id}' not found.")
        return contact

    @staticmethod
    async def create_contact(
        db: AsyncSession, contact_data: ContactCreate, provider_id: str = "local_database"
    ) -> ContactRecord:
        """Create a new contact record."""
        if not contact_data.display_name.strip():
            raise ValidationError("Display name cannot be empty.")

        contact = ContactRecord(
            display_name=contact_data.display_name,
            given_name=contact_data.given_name,
            family_name=contact_data.family_name,
            organization=contact_data.organization,
            emails=contact_data.emails,
            phones=contact_data.phones,
            labels=contact_data.labels,
            provider_id=provider_id,
        )
        db.add(contact)
        await db.commit()
        await db.refresh(contact)
        return contact

    @staticmethod
    async def update_contact(
        db: AsyncSession, contact_id: str, updates: ContactUpdate
    ) -> ContactRecord:
        """Update an existing contact."""
        contact = await ContactsService.get_contact(db, contact_id)

        if updates.display_name is not None:
            contact.display_name = updates.display_name
        if updates.given_name is not None:
            contact.given_name = updates.given_name
        if updates.family_name is not None:
            contact.family_name = updates.family_name
        if updates.organization is not None:
            contact.organization = updates.organization
        if updates.emails is not None:
            contact.emails = updates.emails
        if updates.phones is not None:
            contact.phones = updates.phones
        if updates.labels is not None:
            contact.labels = updates.labels

        await db.commit()
        await db.refresh(contact)
        return contact

    @staticmethod
    async def delete_contact(db: AsyncSession, contact_id: str) -> bool:
        """Delete an authorized contact record."""
        contact = await ContactsService.get_contact(db, contact_id)
        await db.delete(contact)
        await db.commit()
        return True
