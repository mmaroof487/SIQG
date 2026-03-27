"""Column encryption/decryption helpers (AES-256-GCM)."""
import base64
import hashlib
import os
import re
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)


def _normalized_key() -> bytes:
    """
    Return exactly 32 bytes for AES-256.
    If source key length is not 32, derive a fixed-length key via SHA-256.
    """
    raw = (settings.encryption_key or "").encode("utf-8")
    if len(raw) == 32:
        return raw
    return hashlib.sha256(raw).digest()


def _encrypt_columns_set() -> set[str]:
    return {c.lower() for c in settings.encrypt_columns_list}


def encrypt_value(value: str) -> str:
    """Encrypt plaintext using AES-256-GCM and return base64(nonce + ciphertext)."""
    if value is None:
        return value
    if not isinstance(value, str):
        value = str(value)
    nonce = os.urandom(12)
    aesgcm = AESGCM(_normalized_key())
    ciphertext = aesgcm.encrypt(nonce, value.encode("utf-8"), None)
    payload = nonce + ciphertext
    return base64.b64encode(payload).decode("utf-8")


def decrypt_value(value: str):
    """Best-effort decrypt for base64(nonce + ciphertext). Returns original on failure."""
    if value is None or not isinstance(value, str):
        return value
    try:
        data = base64.b64decode(value.encode("utf-8"))
        nonce = data[:12]
        ciphertext = data[12:]
        aesgcm = AESGCM(_normalized_key())
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext.decode("utf-8")
    except Exception:
        return value


def _split_sql_csv(raw: str) -> list[str]:
    """
    Split SQL CSV while respecting quoted commas.
    Minimal parser for INSERT column/value lists and UPDATE SET clause.
    """
    parts = []
    buf = []
    in_single = False
    in_double = False
    i = 0
    while i < len(raw):
        ch = raw[i]
        if ch == "'" and not in_double:
            in_single = not in_single
            buf.append(ch)
        elif ch == '"' and not in_single:
            in_double = not in_double
            buf.append(ch)
        elif ch == "," and not in_single and not in_double:
            parts.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
        i += 1
    if buf:
        parts.append("".join(buf).strip())
    return parts


def _quoted_literal(token: str):
    token = token.strip()
    if len(token) >= 2 and token[0] == "'" and token[-1] == "'":
        return token[1:-1]
    return None


def encrypt_query_values(query: str) -> str:
    """
    Encrypt configured columns for common INSERT/UPDATE SQL statements.
    Leaves query untouched if parsing fails.
    """
    enc_cols = _encrypt_columns_set()
    if not enc_cols:
        return query

    q = query.strip()
    q_upper = q.upper()

    # INSERT INTO t (a,b,c) VALUES ('x', ... )
    insert_match = re.match(
        r"(?is)^\s*INSERT\s+INTO\s+\S+\s*\((?P<cols>[^)]*)\)\s*VALUES\s*\((?P<vals>[^)]*)\)(?P<tail>.*)$",
        q,
    )
    if insert_match:
        cols = [c.strip().strip('"').strip("`") for c in _split_sql_csv(insert_match.group("cols"))]
        vals = _split_sql_csv(insert_match.group("vals"))
        if len(cols) != len(vals):
            return query
        new_vals = []
        for col, val in zip(cols, vals):
            lit = _quoted_literal(val)
            if col.lower() in enc_cols and lit is not None:
                new_vals.append(f"'{encrypt_value(lit)}'")
            else:
                new_vals.append(val)
        return re.sub(
            r"(?is)^\s*INSERT\s+INTO\s+(\S+)\s*\([^)]*\)\s*VALUES\s*\([^)]*\)(.*)$",
            lambda m: f"INSERT INTO {m.group(1)} ({insert_match.group('cols')}) VALUES ({', '.join(new_vals)}){insert_match.group('tail')}",
            q,
            count=1,
        )

    # UPDATE t SET a='x', b='y' WHERE ...
    if q_upper.startswith("UPDATE "):
        update_match = re.match(r"(?is)^\s*UPDATE\s+\S+\s+SET\s+(?P<set>.+?)(\s+WHERE\s+.+)?$", q)
        if not update_match:
            return query
        set_clause = update_match.group("set")
        parts = _split_sql_csv(set_clause)
        new_parts = []
        for part in parts:
            m = re.match(r'(?is)^\s*("?[\w]+"?)\s*=\s*(.+)\s*$', part)
            if not m:
                new_parts.append(part)
                continue
            col = m.group(1).strip().strip('"').strip("`")
            val = m.group(2).strip()
            lit = _quoted_literal(val)
            if col.lower() in enc_cols and lit is not None:
                new_parts.append(f'{m.group(1)} = \'{encrypt_value(lit)}\'')
            else:
                new_parts.append(part)
        return q.replace(set_clause, ", ".join(new_parts), 1)

    return query


def decrypt_rows(rows: list[dict]) -> list[dict]:
    """
    Decrypt configured columns on a copy of rows.
    """
    enc_cols = _encrypt_columns_set()
    if not rows or not enc_cols:
        return rows

    out = []
    for row in rows:
        row_copy = {}
        for key, value in row.items():
            if str(key).lower() in enc_cols:
                row_copy[key] = decrypt_value(value)
            else:
                row_copy[key] = value
        out.append(row_copy)
    return out

