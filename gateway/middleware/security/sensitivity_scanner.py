"""
Sensitivity Scanner — Phase 4.

Automatically discovers columns that likely contain PII or sensitive data
using three independent detectors:

    Tier 1 – Column name regex patterns   (fast, zero DB calls)
    Tier 2 – Dictionary lookup             (curated keyword list)
    Tier 3 – Optional AI heuristics        (extensible hook)

Returns a list of ScanResult objects, one per matched column.  The caller
(connections router) decides whether to persist them as ColumnSecurity rows.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Sequence


# ── Classification methods (mirrors ColumnSecurity.classification_method) ─────
class ClassificationMethod(IntEnum):
    REGEX = 0
    DICTIONARY = 1
    AI = 2
    MANUAL = 3


# ── PII regex patterns for column names ───────────────────────────────────────
_REGEX_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("ssn",         re.compile(r"(^|_)(ssn|social_security|social_sec)($|_)", re.I)),
    ("credit_card", re.compile(r"(^|_)(credit_card|card_number|cc_num|pan)($|_)", re.I)),
    ("email",       re.compile(r"(^|_)(email|e_mail|mail_address)($|_)", re.I)),
    ("phone",       re.compile(r"(^|_)(phone|mobile|cell|telephone|tel)($|_)", re.I)),
    ("dob",         re.compile(r"(^|_)(dob|date_of_birth|birth_date|birthdate)($|_)", re.I)),
    ("passport",    re.compile(r"(^|_)(passport|passport_no|passport_number)($|_)", re.I)),
    ("password",    re.compile(r"(^|_)(password|passwd|pass_hash|hashed_password)($|_)", re.I)),
    ("ip_address",  re.compile(r"(^|_)(ip_address|ip_addr|client_ip|remote_ip)($|_)", re.I)),
    ("bank_account",re.compile(r"(^|_)(bank_account|account_number|iban|routing)($|_)", re.I)),
    ("salary",      re.compile(r"(^|_)(salary|wage|compensation|pay_rate)($|_)", re.I)),
    ("address",     re.compile(r"(^|_)(street_address|home_address|billing_address|postal)($|_)", re.I)),
    ("tax_id",      re.compile(r"(^|_)(tax_id|taxid|tin|ein|vat_number)($|_)", re.I)),
    ("health",      re.compile(r"(^|_)(diagnosis|medical_record|patient_id|health_plan)($|_)", re.I)),
    ("biometric",   re.compile(r"(^|_)(fingerprint|retina|face_id|biometric)($|_)", re.I)),
]

# ── Dictionary lookup (broader set of sensitive keywords) ─────────────────────
_DICTIONARY_KEYWORDS: frozenset[str] = frozenset({
    "secret", "token", "api_key", "private_key", "access_token",
    "refresh_token", "auth_token", "session_token",
    "pin", "cvv", "cvc", "expiry", "expiration",
    "gender", "race", "ethnicity", "nationality",
    "religion", "political_view",
    "income", "net_worth", "credit_score",
    "license_number", "drivers_license",
    "voter_id", "national_id",
    "device_id", "imei", "mac_address",
    "location", "gps", "latitude", "longitude",
})


@dataclass
class ScanResult:
    """A single PII-candidate column detected by the scanner."""
    schema_name: str
    table_name: str
    column_name: str
    classification_method: ClassificationMethod
    label: str                          # human-readable label (e.g. "email")
    confidence: float = 1.0            # 0.0 – 1.0
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "schema_name": self.schema_name,
            "table_name": self.table_name,
            "column_name": self.column_name,
            "classification_method": int(self.classification_method),
            "label": self.label,
            "confidence": self.confidence,
        }


async def scan_columns(
    schema_info: Sequence[dict],
    *,
    run_ai: bool = False,
) -> list[ScanResult]:
    """
    Scan a list of column descriptors for PII/sensitive data.

    Args:
        schema_info: list of dicts with keys:
            schema_name, table_name, column_name, data_type (optional)
        run_ai: if True, runs the AI tier

    Returns:
        Deduplicated list of ScanResult, ordered by table then column.
    """
    results: list[ScanResult] = []
    seen: set[tuple[str, str, str]] = set()

    for col in schema_info:
        schema = col.get("schema_name", "public")
        table = col["table_name"]
        column = col["column_name"]
        key = (schema, table, column)

        if key in seen:
            continue

        col_lower = column.lower()

        # Tier 1 – Regex
        for label, pattern in _REGEX_PATTERNS:
            if pattern.search(col_lower):
                results.append(ScanResult(
                    schema_name=schema,
                    table_name=table,
                    column_name=column,
                    classification_method=ClassificationMethod.REGEX,
                    label=label,
                    confidence=0.95,
                ))
                seen.add(key)
                break

        if key in seen:
            continue

        # Tier 2 – Dictionary
        # Check if any dictionary keyword is a substring of the column name
        for keyword in _DICTIONARY_KEYWORDS:
            if keyword in col_lower:
                results.append(ScanResult(
                    schema_name=schema,
                    table_name=table,
                    column_name=column,
                    classification_method=ClassificationMethod.DICTIONARY,
                    label=keyword,
                    confidence=0.75,
                ))
                seen.add(key)
                break

    # Tier 3 – AI
    if run_ai:
        unscanned = [
            col for col in schema_info
            if (col.get("schema_name", "public"), col["table_name"], col["column_name"])
            not in seen
        ]
        if unscanned:
            ai_results = await _ai_scan(unscanned)
            results.extend(ai_results)

    return sorted(results, key=lambda r: (r.table_name, r.column_name))


async def _ai_scan(columns: Sequence[dict]) -> list[ScanResult]:
    """
    AI-based sensitivity detection.
    """
    from routers.v1.ai import call_llm
    import json
    
    if not columns:
        return []

    system_prompt = """You are a database security expert.
Analyze the following list of database columns and identify which ones are likely to contain sensitive data or PII (Personally Identifiable Information).
Return ONLY valid JSON in this exact format, with no markdown formatting:
{
    "sensitive_columns": [
        {
            "schema_name": "...",
            "table_name": "...",
            "column_name": "...",
            "label": "Brief reason (e.g. email, password, address)"
        }
    ]
}
If no columns are sensitive, return {"sensitive_columns": []}."""

    user_message = json.dumps([
        {
            "schema_name": col.get("schema_name", "public"),
            "table_name": col["table_name"],
            "column_name": col["column_name"],
            "data_type": col.get("data_type", "unknown")
        } for col in columns
    ])

    results = []
    try:
        response = await call_llm(system_prompt, user_message)
        if response.startswith("ERROR:"):
            from utils.logger import get_logger
            get_logger(__name__).error(f"AI scan failed: {response}")
            return []
            
        data = json.loads(response)
        sensitive = data.get("sensitive_columns", [])
        for item in sensitive:
            results.append(ScanResult(
                schema_name=item.get("schema_name", "public"),
                table_name=item.get("table_name", ""),
                column_name=item.get("column_name", ""),
                classification_method=ClassificationMethod.AI,
                label=item.get("label", "AI Detected"),
                confidence=0.85,
            ))
    except Exception as e:
        from utils.logger import get_logger
        get_logger(__name__).error(f"AI scan JSON parsing failed: {e}")
        
    return results
