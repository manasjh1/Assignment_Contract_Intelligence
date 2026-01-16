from pydantic import BaseModel

class ExtractResponse(BaseModel):
    parties: list[str]
    effective_date: str | None
    term: str | None
    governing_law: str | None
    payment_terms: str | None
    termination_clause: str | None
    liability_cap: str | None

class AskRequest(BaseModel):
    question: str

class AuditFinding(BaseModel):
    risk_category: str
    severity: str
    evidence: str
    explanation: str

class AuditResponse(BaseModel):
    risks: list[AuditFinding]


class WebhookRequest(BaseModel):
    callback_url: str
    task_type: str = "audit_simulation"    