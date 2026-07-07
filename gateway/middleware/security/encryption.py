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


def encrypt_value(value: str, key: bytes = None) -> str:
    """Encrypt plaintext using AES-256-GCM and return base64(nonce + ciphertext)."""
    if value is None:
        return value
    if not isinstance(value, str):
        value = str(value)
    nonce = os.urandom(12)
    aesgcm = AESGCM(key if key else _normalized_key())
    ciphertext = aesgcm.encrypt(nonce, value.encode("utf-8"), None)
    payload = nonce + ciphertext
    return base64.b64encode(payload).decode("utf-8")


def decrypt_value(value: str, key: bytes = None):
    """Best-effort decrypt for base64(nonce + ciphertext). Returns original on failure."""
    if value is None or not isinstance(value, str):
        return value
    try:
        data = base64.b64decode(value.encode("utf-8"))
        nonce = data[:12]
        ciphertext = data[12:]
        aesgcm = AESGCM(key if key else _normalized_key())
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext.decode("utf-8")
    except Exception as e:
        logger.warning(f"Decryption failed, returning original value: {e}")
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


def encrypt_query_values_for_columns(query: str, columns: list[str]) -> str:
    """
    Variant of encrypt_query_values() that uses an explicit column list
    (for per-connection encryption config in Phase B external connections).
    """
    if not columns:
        return query
    enc_cols = {c.lower() for c in columns if c}
    # Temporarily swap the settings-based column set by delegating to the
    # same regex path, passing enc_cols explicitly.
    return _encrypt_with_cols(query, enc_cols)


def decrypt_rows_for_columns(rows: list[dict], columns: list[str]) -> list[dict]:
    """
    Variant of decrypt_rows() that uses an explicit column list
    (for per-connection encryption config in Phase B external connections).
    """
    if not rows or not columns:
        return rows
    enc_cols = {c.lower() for c in columns if c}
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


def _encrypt_with_cols(query: str, enc_cols: set) -> str:
    """
    Internal: apply AES encryption to INSERT/UPDATE values for the given column set.
    Same logic as encrypt_query_values() but accepts an explicit set.
    """
    import re
    q = query.strip()
    upper_q = q.upper()

    # INSERT INTO table (col1, col2, ...) VALUES (val1, val2, ...)
    if upper_q.startswith("INSERT"):
        cols_match = re.search(r"INSERT\s+INTO\s+\w+\s*\(([^)]+)\)", q, re.IGNORECASE)
        vals_match = re.search(r"VALUES\s*\(([^)]+)\)", q, re.IGNORECASE)
        if cols_match and vals_match:
            col_names = [c.strip().strip('"').strip("`").lower() for c in cols_match.group(1).split(",")]
            raw_vals = vals_match.group(1)
            val_parts = [v.strip() for v in re.split(r",(?=(?:[^']*'[^']*')*[^']*$)", raw_vals)]
            if len(col_names) == len(val_parts):
                new_vals = []
                for col, val in zip(col_names, val_parts):
                    lit = _quoted_literal(val)
                    if col in enc_cols and lit is not None:
                        new_vals.append(f"'{encrypt_value(lit)}'")
                    else:
                        new_vals.append(val)
                new_vals_str = ", ".join(new_vals)
                q = q.replace(vals_match.group(0), f"VALUES ({new_vals_str})", 1)
        return q

    # UPDATE table SET col1 = val1, col2 = val2 WHERE ...
    if upper_q.startswith("UPDATE"):
        set_match = re.search(r"SET\s+(.+?)(?:\s+WHERE\s+|$)", q, re.IGNORECASE | re.DOTALL)
        if set_match:
            set_clause = set_match.group(1)
            parts = re.split(r",(?=(?:[^']*'[^']*')*[^']*$)", set_clause)
            new_parts = []
            for part in parts:
                m = re.match(r"\s*(\w+)\s*=\s*(.+)", part.strip())
                if not m:
                    new_parts.append(part)
                    continue
                col = m.group(1).strip().strip('"').strip("`")
                val = m.group(2).strip()
                lit = _quoted_literal(val)
                if col.lower() in enc_cols and lit is not None:
                    new_parts.append(f"{m.group(1)} = '{encrypt_value(lit)}'")
                else:
                    new_parts.append(part)
            return q.replace(set_clause, ", ".join(new_parts), 1)

    return query

