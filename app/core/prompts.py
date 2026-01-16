from langchain_core.prompts import PromptTemplate

# 1. Extraction Prompt
EXTRACT_TEMPLATE = """
You are an expert legal contract analyst. 
Extract the following entities from the contract text provided below.
Output must be strictly valid JSON matching the requested schema.
If a field is not found, use null.

Context:
{context}

Format instructions:
{format_instructions}
"""

EXTRACT_PROMPT = PromptTemplate(
    template=EXTRACT_TEMPLATE,
    input_variables=["context", "format_instructions"]
)

# 2. Audit/Risk Prompt
AUDIT_TEMPLATE = """
You are a senior legal risk auditor. Review the clauses below for HIGH RISK factors.

Risks to Flag:
1. **Auto-renewal**: Any auto-renewal with less than 30 days notice.
2. **Liability**: Unlimited liability or caps exceeding 5x contract value.
3. **Indemnity**: Broad or one-sided indemnification clauses.
4. **Termination**: Termination for convenience without notice.

Contract Text:
{context}

Return a JSON list of objects. Each object must have:
- "risk_category": string
- "severity": "HIGH" or "MEDIUM"
- "evidence": string (exact quote from text)
- "explanation": string (why it is risky)
"""

AUDIT_PROMPT = PromptTemplate(
    template=AUDIT_TEMPLATE,
    input_variables=["context"]
)