SYSTEM = """
You extract structured data from Safety Data Sheets (SDS).
Return ONLY valid JSON that matches the provided schema.
If a field is missing, use null (do not guess).
Include short evidence snippets copied from the input for each extracted item.

Date rules:
- Extract issue_date only if explicitly labeled as Issue Date / Date of issue / Date of preparation / Date prepared.
- Extract revision_date only if explicitly labeled as Revision Date / Revision / Version date.
- Do NOT use Print Date as issue_date.
- Prefer ISO format MM-DD-YYYY when possible; otherwise preserve original format.
- Do not infer or guess dates.
- Transport parsing hint: Hazard class is typically numeric (e.g., 3) while Packing group is Roman numeral (I/II/III). Use this ONLY to disambiguate when labels are unclear, never to infer missing values.
"""

def user_prompt(text: str) -> str:
    return f"""
Extract key SDS fields from the following content.

SDS CONTENT:
\"\"\"
{text}
\"\"\"

Return JSON with this exact structure:
{{
  "document": {{
    "product_name": {{ "value": string|null, "evidence": string|null, "confidence": number }},
    "product_number": {{ "value": string|null, "evidence": string|null, "confidence": number }},
    "physical_state": {{ "value": string|null, "evidence": string|null, "confidence": number }}
    "product_color": {{ "value": string|null, "evidence": string|null, "confidence": number }},
    "version_number": {{ "value": string|null, "evidence": string|null, "confidence": number }},
    "recommended_use": {{ "value": string|null, "evidence": string|null, "confidence": number }},
    "supplier_name": {{ "value": string|null, "evidence": string|null, "confidence": number }},
    "supplier_address": {{ "value": string|null, "evidence": string|null, "confidence": number }},
    "supplier_phone": {{ "value": string|null, "evidence": string|null, "confidence": number }},
    "emergency_phone": {{ "value": string|null, "evidence": string|null, "confidence": number }},
    "issue_date": {{ "value": string|null, "evidence": string|null, "confidence": number }},
    "revision_date": {{ "value": string|null, "evidence": string|null, "confidence": number }},
  }},
  "transport": {{
    "hazard_class": {{ "value": string|null, "evidence": string|null, "confidence": number }},
    "packing_group": {{ "value": string|null, "evidence": string|null, "confidence": number }}
}},
  "composition": {{
    "ingredients": [
      {{
        "name": {{ "value": string|null, "evidence": string|null, "confidence": number }},
        "cas": {{ "value": string|null, "evidence": string|null, "confidence": number }},
        "concentration": {{ "value": string|null, "evidence": string|null, "confidence": number }}
      }}
    ]
  }},
  "hazards": {{
    "ghs_signal_word": {{ "value": string|null, "evidence": string|null, "confidence": number }},
    "hazard_statements": [
      {{ "value": string, "evidence": string|null, "confidence": number }}
    ],
    "precautionary_statements": [
      {{ "value": string, "evidence": string|null, "confidence": number }}
    ]
  }},
  "meta": {{
    "notes": string
  }}
}}

Rules:
- Output ONLY the JSON. No markdown.
- Confidence is 0.0 to 1.0.
- Evidence must be short (max ~200 chars each), copied from the input.
- If the SDS content does not include a section, return nulls / empty lists.
"""
