"""
AST-based Query Encryption Pipeline — Phase 5 & 6.

Architecture:
    QueryEncryptor.encrypt_query()  — rewrites INSERT/UPDATE literals → ciphertext
    QueryEncryptor.decrypt_results() — decrypts SELECT result columns → plaintext

Single code path for every encryption operation.  All cryptography flows
through KeyManager → per-connection DEK.  No regex, no env-column lists.

Usage:
    encryptor = QueryEncryptor(
        dek=dek_bytes,                       # 32-byte AES-256 key for this DB
        encrypted_columns={"users": {"ssn", "credit_card"}},
    )
    safe_query = encryptor.encrypt_query(raw_sql)
    plain_rows  = encryptor.decrypt_results(raw_rows)
"""
from __future__ import annotations

import base64
import os
import time
from dataclasses import dataclass, field
from typing import Any

import sqlglot
from sqlglot import exp

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from utils.logger import get_logger

logger = get_logger(__name__)

# ── Ciphertext envelope format ─────────────────────────────────────────────────
# v1 binary layout: [1 byte version][2 bytes key_id][12 bytes nonce][remaining ciphertext+tag]
# Base64-encoded to fit in a TEXT/VARCHAR column.
_ENVELOPE_VERSION: int = 1


def _pack(key_id: int, nonce: bytes, ciphertext: bytes) -> str:
    """Encode version + key_id + nonce + ciphertext → base64 string."""
    import struct
    # >BH : big-endian, 1 byte unsigned char (version), 2 bytes unsigned short (key_id)
    header = struct.pack(">BH", _ENVELOPE_VERSION, key_id)
    raw = header + nonce + ciphertext
    return base64.b64encode(raw).decode("ascii")


def _unpack(encoded: str) -> tuple[int, bytes, bytes] | None:
    """Decode base64 → (key_id, nonce, ciphertext).  Returns None on malformed input."""
    import struct
    try:
        raw = base64.b64decode(encoded.encode("ascii"))
    except Exception:
        return None
    if len(raw) < 16:  # 1 (version) + 2 (key_id) + 12 (nonce) + 1 (min ciphertext)
        return None
    version = raw[0]
    if version != _ENVELOPE_VERSION:
        # Unknown version — caller can decide how to handle
        logger.debug("Unknown ciphertext envelope version: %d", version)
        return None
    _, key_id = struct.unpack(">BH", raw[:3])
    return key_id, raw[3:15], raw[15:]


# ── Core AES-256-GCM helpers ──────────────────────────────────────────────────

def _aes_encrypt(plaintext: str, dek: bytes, key_version: int) -> str:
    """Encrypt a string with AES-256-GCM, return versioned envelope."""
    nonce = os.urandom(12)
    aesgcm = AESGCM(dek)
    ct = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return _pack(key_version, nonce, ct)


def _aes_decrypt(encoded: str, dek: bytes, historic_deks: dict[int, bytes] = None) -> str:
    """Decrypt a versioned envelope.  Returns original string on failure (best-effort)."""
    # Note: Phase 9/11 will load dek dynamically based on key_id if historical deks are used.
    # Currently assumes the provided dek is the correct one.
    unpacked = _unpack(encoded)
    if unpacked is None:
        return encoded   # not our ciphertext — pass through unchanged
    key_id, nonce, ct = unpacked
    target_dek = dek
    if historic_deks and key_id in historic_deks:
        target_dek = historic_deks[key_id]

    try:
        aesgcm = AESGCM(target_dek)
        plain = aesgcm.decrypt(nonce, ct, None)
        return plain.decode("utf-8")
    except Exception as exc:
        logger.warning("Decryption failed for value (first 20 chars: %r): %s", encoded[:20], exc)
        return encoded


# ── Column-map type alias ─────────────────────────────────────────────────────
#    { "table_name": {"col1", "col2"} }
ColumnMap = dict[str, set[str]]


@dataclass
class QueryEncryptor:
    """
    Stateless-per-request query rewriter.

    Attributes:
        dek:               32-byte Data Encryption Key for this database connection.
        key_version:       Integer version of the DEK.
        encrypted_columns: Mapping of table_name → set of column names to encrypt.
    """
    dek: bytes
    key_version: int
    encrypted_columns: ColumnMap = field(default_factory=dict)
    historic_deks: dict[int, bytes] = field(default_factory=dict)
    values_encrypted: int = field(default=0, init=False)
    columns_encrypted: set[str] = field(default_factory=set, init=False)
    values_decrypted: int = field(default=0, init=False)
    columns_decrypted: set[str] = field(default_factory=set, init=False)
    encrypt_time_ms: float = field(default=0.0, init=False)
    decrypt_time_ms: float = field(default=0.0, init=False)

    def _should_encrypt(self, table: str, column: str) -> bool:
        """Return True if this (table, column) pair must be encrypted."""
        cols = self.encrypted_columns.get(table.lower(), set())
        return column.lower() in cols

    # ── Public API ─────────────────────────────────────────────────────────────

    def encrypt_query(self, sql: str, dialect: str = "postgres") -> str:
        """
        Parse SQL and replace string literals in INSERT/UPDATE with ciphertext.

        Handles:
            INSERT INTO t (a, b) VALUES ('x', 'y')
            INSERT INTO t (a, b) VALUES (...), (...)    ← multi-row
            INSERT INTO t ... SELECT ...                 ← SELECT source (skip)
            UPDATE t SET a = 'x', b = 'y' WHERE ...
            WITH cte AS (...) INSERT / UPDATE            ← CTE wrapper
            Parameterized queries ($1, ?, :name)         ← skipped safely

        Returns original SQL on any parse error.
        """
        self.values_encrypted = 0
        self.columns_encrypted = set()
        self.encrypt_time_ms = 0.0

        if not self.encrypted_columns:
            return sql
        try:
            _t0 = time.perf_counter()
            tree = sqlglot.parse_one(sql, read=dialect, error_level=sqlglot.ErrorLevel.IGNORE)
        except Exception as exc:
            logger.warning("query_encryptor: parse failed — %s", exc)
            return sql

        modified = self._rewrite_node(tree)
        if not modified:
            return sql
        try:
            result = tree.sql(dialect=dialect, pretty=False)
            self.encrypt_time_ms = (time.perf_counter() - _t0) * 1000
            return result
        except Exception as exc:
            logger.warning("query_encryptor: sql() serialization failed — %s", exc)
            return sql

    def decrypt_results(
        self,
        rows: list[dict[str, Any]],
        table: str,
    ) -> list[dict[str, Any]]:
        """
        Decrypt ciphertext values in query result rows.

        Args:
            rows:  List of result row dicts (column_name → value).
            table: The primary table these rows came from.

        Returns a new list with decrypted values; original rows are unchanged.
        """
        target_cols = self.encrypted_columns.get(table.lower(), set())
        if not rows or not target_cols:
            return rows

        _t0 = time.perf_counter()
        out: list[dict[str, Any]] = []
        for row in rows:
            new_row: dict[str, Any] = {}
            for col, val in row.items():
                if col.lower() in target_cols and isinstance(val, str):
                    new_val = _aes_decrypt(val, self.dek, self.historic_deks)
                    if new_val != val:
                        self.values_decrypted += 1
                        self.columns_decrypted.add(col.lower())
                    new_row[col] = new_val
                else:
                    new_row[col] = val
            out.append(new_row)
        self.decrypt_time_ms = (time.perf_counter() - _t0) * 1000
        return out

    # ── Private AST rewriting ──────────────────────────────────────────────────

    def _rewrite_node(self, node: exp.Expression) -> bool:
        """
        Recursively walk the AST, rewriting INSERT/UPDATE nodes in-place.
        Returns True if at least one value was modified.
        """
        modified = False
        if isinstance(node, exp.Insert):
            modified |= self._rewrite_insert(node)
        elif isinstance(node, exp.Update):
            modified |= self._rewrite_update(node)
        # Recurse into CTE bodies and sub-selects
        for child in node.args.values():
            if isinstance(child, exp.Expression):
                modified |= self._rewrite_node(child)
            elif isinstance(child, list):
                for item in child:
                    if isinstance(item, exp.Expression):
                        modified |= self._rewrite_node(item)
        return modified

    def _rewrite_insert(self, node: exp.Insert) -> bool:
        """Rewrite INSERT … VALUES … nodes."""
        modified = False

        # Determine table name
        table_node = node.args.get("this")
        if table_node is None:
            return False
        table_name = (
            table_node.name
            if isinstance(table_node, exp.Table)
            else str(table_node)
        )
        table_name = table_name.lower()

        # Extract column names from column list
        schema_node = table_node
        # sqlglot puts columns into Insert.args["this"] (a Schema) or separate
        columns_node = node.args.get("columns")
        if columns_node:
            col_names = [c.name.lower() for c in columns_node]
        elif isinstance(table_node, exp.Schema):
            col_names = [c.name.lower() for c in table_node.expressions]
            table_name = table_node.this.name.lower()
        else:
            return False   # can't identify columns — skip

        target_cols = self.encrypted_columns.get(table_name, set())
        if not target_cols:
            return False

        # Find the VALUES expression
        expression_node = node.args.get("expression")
        if not isinstance(expression_node, exp.Values):
            return False   # INSERT … SELECT — skip

        for tuple_node in expression_node.expressions:
            if not isinstance(tuple_node, (exp.Tuple, exp.Anonymous)):
                # Could be exp.Tuple or a bare expressions list
                values = tuple_node.expressions if hasattr(tuple_node, "expressions") else []
            else:
                def _encrypt_literal(node: exp.Expression) -> exp.Expression:
                    if isinstance(node, (exp.Literal, exp.Boolean, exp.Null)):
                        if isinstance(node, exp.Null) or str(node).upper() == "NULL":
                            return node  # Don't encrypt NULLs
                        val_str = node.name if isinstance(node, exp.Literal) else str(node.this)
                        enc_val = _aes_encrypt(val_str, self.dek, self.key_version)
                        return exp.Literal.string(enc_val)
                    return node
                values = tuple_node.expressions
                for idx, val_node in enumerate(values):
                    if idx < len(col_names) and col_names[idx] in target_cols:
                        new_val = _encrypt_literal(val_node)
                        if new_val is not val_node:
                            tuple_node.expressions[idx] = new_val
                            self.values_encrypted += 1
                            self.columns_encrypted.add(col_names[idx])
                            modified = True

        return modified

    def _rewrite_update(self, node: exp.Update) -> bool:
        """Rewrite UPDATE … SET … nodes."""
        modified = False

        table_node = node.args.get("this")
        if table_node is None:
            return False
        table_name = (
            table_node.name
            if isinstance(table_node, exp.Table)
            else str(table_node)
        ).lower()

        target_cols = self.encrypted_columns.get(table_name, set())
        if not target_cols:
            return False

        for eq_node in (node.args.get("expressions") or []):
            if not isinstance(eq_node, exp.EQ):
                continue
            left = eq_node.args.get("this")
            right = eq_node.args.get("expression")
            if left is None or right is None:
                continue
            col_name = left.name.lower() if hasattr(left, "name") else str(left).lower()
            if col_name in target_cols and isinstance(right, exp.Literal) and right.is_string:
                ciphertext = _aes_encrypt(right.this, self.dek, self.key_version)
                eq_node.args["expression"] = exp.Literal.string(ciphertext)
                self.values_encrypted += 1
                self.columns_encrypted.add(col_name)
                modified = True

        return modified


# ── Factory helper ─────────────────────────────────────────────────────────────

def make_encryptor(dek: bytes, key_version: int, column_security_rows: list, historic_deks: dict[int, bytes] = None) -> QueryEncryptor:
    """
    Build a QueryEncryptor from a list of ColumnSecurity ORM rows.

    Args:
        dek:                  Per-connection DEK (bytes).
        key_version:          Integer version of the DEK.
        column_security_rows: Iterable of ColumnSecurity model instances
                              (must have .table_name, .column_name, .is_encrypted).
        historic_deks:        Optional mapping of old key_version -> historic DEK bytes.

    Returns:
        Configured QueryEncryptor ready for use.
    """
    col_map: ColumnMap = {}
    for row in column_security_rows:
        if not row.is_encrypted:
            continue
        tbl = row.table_name.lower()
        if tbl not in col_map:
            col_map[tbl] = set()
        col_map[tbl].add(row.column_name.lower())
    historic_deks = historic_deks or {}
    return QueryEncryptor(dek=dek, key_version=key_version, encrypted_columns=col_map, historic_deks=historic_deks)
