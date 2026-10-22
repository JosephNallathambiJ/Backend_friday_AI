# Contacts Integration & Privacy Minimization

## 1. Overview

FRIDAY AI provides a normalized contacts model and provider interface (`app/services/contacts_service.py`) for managing address book records safely.

## 2. Normalized Contact Model

```python
class ContactRecord:
    id: str  # UUID
    display_name: str
    given_name: str | None
    family_name: str | None
    organization: str | None
    emails: list[str]
    phones: list[str]
    labels: list[str]
    provider_id: str
    created_at: datetime
    updated_at: datetime
```

## 3. Privacy Safeguards
- **Least-Privilege Exposure**: Contact lists are never dumped entirely into LLM prompts. Only matching search records are returned.
- **Audit Sanitization**: Audit logs record contact IDs and operation types, never full phone numbers or email dumps.
- **Approval on Destruction**: Deleting a contact requires the `contacts.write` capability and human approval.

## 4. API Endpoints

- `GET /api/v1/contacts`: List contacts or search via `?query=...`
- `POST /api/v1/contacts`: Create a new contact.
- `GET /api/v1/contacts/{id}`: Retrieve contact details.
- `PATCH /api/v1/contacts/{id}`: Update contact fields.
- `DELETE /api/v1/contacts/{id}`: Delete contact record.
