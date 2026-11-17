"""Small async HubSpot CRM adapter using a tenant-scoped access token.

For production, provision tokens via HubSpot OAuth, encrypt refresh/access tokens
at rest per tenant, rotate them, and pass the decrypted short-lived token here.
"""
import httpx
from datetime import datetime, timezone

HUBSPOT_API = "https://api.hubapi.com"


class HubSpotClient:
    def __init__(self, access_token: str, timeout_seconds: float = 15.0):
        if not access_token:
            raise ValueError("A tenant-scoped HubSpot access token is required")
        self.access_token = access_token
        self.timeout_seconds = timeout_seconds

    async def upsert_company(self, company: dict) -> dict:
        domain = str(company.get("domain", "")).strip().lower()
        if not domain:
            raise ValueError("Company domain is required")
        properties = {
            "name": company.get("name", domain),
            "domain": domain,
            "industry": company.get("industry") or "",
            "numberofemployees": str(company.get("employee_count") or ""),
            "country": company.get("country") or "",
            "description": company.get("description") or "",
        }
        headers = {"Authorization": f"Bearer {self.access_token}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            lookup = await client.get(f"{HUBSPOT_API}/crm/v3/objects/companies/{domain}",
                                      params={"idProperty": "domain"}, headers=headers)
            if lookup.status_code == 200:
                object_id = lookup.json()["id"]
                response = await client.patch(f"{HUBSPOT_API}/crm/v3/objects/companies/{object_id}",
                                              json={"properties": properties}, headers=headers)
            elif lookup.status_code == 404:
                response = await client.post(f"{HUBSPOT_API}/crm/v3/objects/companies",
                                             json={"properties": properties}, headers=headers)
            else:
                lookup.raise_for_status()
                raise RuntimeError("Unexpected HubSpot lookup response")
            response.raise_for_status()
            return response.json()


    async def create_company_note(self, domain: str, body: str) -> dict:
        """Create a CRM note and associate it with the company matching domain."""
        headers = {"Authorization": f"Bearer {self.access_token}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            lookup = await client.get(f"{HUBSPOT_API}/crm/v3/objects/companies/{domain}",
                                      params={"idProperty": "domain", "properties": "name,domain"}, headers=headers)
            lookup.raise_for_status()
            company_id = lookup.json()["id"]
            response = await client.post(f"{HUBSPOT_API}/crm/v3/objects/notes", headers=headers, json={
                "properties": {"hs_note_body": body, "hs_timestamp": datetime.now(timezone.utc).isoformat()},
                "associations": [{"to": {"id": company_id}, "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 190}]}]
            })
            response.raise_for_status()
            return response.json()
