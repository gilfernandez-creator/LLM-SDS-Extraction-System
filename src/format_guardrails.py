from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List

# CAS format: 2-7 digits, dash, 2 digits, dash, 1 digit
CAS_RE = re.compile(r"^\d{2,7}-\d{2}-\d$")

# Date format required: MM-DD-YYYY
US_DATE_RE = re.compile(r"^\d{2}-\d{2}-\d{4}$")

# Common unicode dashes to normalize → "-"
DASHES = {
    "\u2010": "-",  # hyphen
    "\u2011": "-",  # non-breaking hyphen
    "\u2012": "-",  # figure dash
    "\u2013": "-",  # en dash
    "\u2014": "-",  # em dash
    "\u2212": "-",  # minus sign
}


def _warn(
    warnings: List[Dict[str, Any]],
    field: str,
    rule: str,
    message: str,
    value: Any = None,
) -> None:
    w: Dict[str, Any] = {"field": field, "rule": rule, "message": message}
    if value is not None:
        w["value"] = value
    warnings.append(w)


def normalize_cas(cas: str) -> str:
    """Normalize dash characters and spacing in CAS values."""
    s = cas.strip()
    for k, v in DASHES.items():
        s = s.replace(k, v)
    # remove spaces around dashes
    s = re.sub(r"\s*-\s*", "-", s)
    return s


def validate_cas_value(cas: str) -> bool:
    return bool(CAS_RE.match(cas))


def validate_us_date(value: str) -> bool:
    """Validate MM-DD-YYYY format and actual calendar validity."""
    s = value.strip()
    if not US_DATE_RE.match(s):
        return False
    try:
        datetime.strptime(s, "%m-%d-%Y")
        return True
    except Exception:
        return False


def apply_format_guardrails(parsed: Dict[str, Any], normalize: bool = True) -> List[Dict[str, Any]]:
    """
    Minimal, warn-only format guardrails:
      - CAS normalization + validation
      - MM-DD-YYYY date validation (issue_date, revision_date)
    No other checks. No repairs. No evidence logic. No date comparisons.
    """
    warnings: List[Dict[str, Any]] = []

    # ---- CAS: composition.ingredients[*].cas.value ----
    comp = parsed.get("composition", {})
    ingredients = comp.get("ingredients", [])
    if isinstance(ingredients, list):
        for i, ing in enumerate(ingredients):
            if not isinstance(ing, dict):
                continue
            cas_obj = ing.get("cas")
            if not isinstance(cas_obj, dict):
                continue
            cas_val = cas_obj.get("value")
            if not isinstance(cas_val, str) or not cas_val.strip():
                continue

            norm = normalize_cas(cas_val)
            if normalize and norm != cas_val:
                cas_obj["value"] = norm

            if not validate_cas_value(norm):
                _warn(
                    warnings,
                    f"composition.ingredients[{i}].cas.value",
                    "cas_format",
                    "CAS number does not match expected pattern #######-##-#.",
                    norm,
                )

    # ---- Dates: document.issue_date.value / document.revision_date.value ----
    doc = parsed.get("document", {})
    for k in ("issue_date", "revision_date"):
        obj = doc.get(k)
        if not isinstance(obj, dict):
            continue
        v = obj.get("value")
        if v is None:
            continue
        if not isinstance(v, str) or not v.strip():
            continue

        if not validate_us_date(v):
            _warn(
                warnings,
                f"document.{k}.value",
                "date_format",
                "Date is not a valid MM-DD-YYYY date.",
                v,
            )

    return warnings
