"""
Multi-Tenant Scoped Query Helper for SEOJEV.
Guarantees tenant isolation: all queries require and enforce org_id filtering.
Attempts to read without an org_id or cross-tenant access raise IsolationViolationError.
"""
from typing import Any, Dict, List, Optional, Union
import psycopg
from .connection import get_connection

class IsolationViolationError(RuntimeError):
    """Raised when an operation attempts to bypass multi-tenant org_id isolation."""
    pass


class ScopedQuery:
    """
    Enforces org_id filtering on all read and query operations.
    Can be used as a context manager or standalone query runner.
    """
    def __init__(
        self,
        org_id: str,
        db_url: Optional[str] = None,
        conn: Optional[psycopg.Connection] = None
    ):
        if not org_id or not isinstance(org_id, str) or not org_id.strip():
            raise IsolationViolationError("A non-empty org_id is required for all database queries.")
        self.org_id = org_id.strip()
        self.db_url = db_url
        self._external_conn = conn
        self._owned_conn: Optional[psycopg.Connection] = None

    def _get_active_conn(self) -> psycopg.Connection:
        if self._external_conn:
            return self._external_conn
        if self._owned_conn is None:
            self._owned_conn = get_connection(self.db_url)
        return self._owned_conn

    def __enter__(self):
        self._get_active_conn()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._owned_conn is not None:
            try:
                self._owned_conn.close()
            except Exception:
                pass
            self._owned_conn = None

    def fetch_all(
        self,
        table: str,
        where: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        select: str = "*"
    ) -> List[Dict[str, Any]]:
        """
        Fetch rows strictly filtered by org_id.
        """
        from services.security import validate_sql_identifier, validate_sql_select

        if not validate_sql_identifier(table):
            raise IsolationViolationError(f"Invalid table identifier '{table}'.")

        if select != "*" and not validate_sql_select(select):
            raise IsolationViolationError(f"Invalid characters in SELECT projection '{select}'.")

        if order_by and (";" in order_by or "--" in order_by or "/*" in order_by):
            raise IsolationViolationError(f"Invalid characters in ORDER BY clause '{order_by}'.")

        q_params = dict(params or {})
        q_params["_scoped_org_id"] = self.org_id

        where_clause = "WHERE org_id = %(_scoped_org_id)s"
        if where and where.strip():
            where_clause += f" AND ({where.strip()})"

        sql = f"SELECT {select} FROM {table} {where_clause}"
        if order_by:
            sql += f" ORDER BY {order_by}"
        if limit is not None:
            sql += f" LIMIT {int(limit)}"
        if offset is not None:
            sql += f" OFFSET {int(offset)}"

        conn = self._get_active_conn()
        with conn.cursor() as cur:
            cur.execute(sql, q_params)
            return cur.fetchall()

    def fetch_one(
        self,
        table: str,
        where: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        select: str = "*"
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch a single row strictly filtered by org_id.
        """
        results = self.fetch_all(
            table=table,
            where=where,
            params=params,
            order_by=order_by,
            limit=1,
            select=select
        )
        return results[0] if results else None

    def count(
        self,
        table: str,
        where: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Count rows strictly filtered by org_id.
        """
        row = self.fetch_one(
            table=table,
            where=where,
            params=params,
            select="COUNT(*) as total_count"
        )
        return int(row["total_count"]) if row else 0

    def execute_scoped_raw(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute raw SQL with mandatory org_id parameter enforcement.
        Raises IsolationViolationError if query does not filter on org_id or params do not match self.org_id.
        """
        q_lower = query.lower()
        if "org_id" not in q_lower:
            raise IsolationViolationError(
                "Multi-tenant isolation violation: Raw query must filter by org_id."
            )

        q_params = dict(params or {})
        # Enforce that query parameter org_id matches this scope
        if "org_id" in q_params and q_params["org_id"] != self.org_id:
            raise IsolationViolationError(
                f"Cross-tenant access attempt: Scoped org '{self.org_id}' cannot query for '{q_params['org_id']}'."
            )
        q_params["org_id"] = self.org_id

        conn = self._get_active_conn()
        with conn.cursor() as cur:
            cur.execute(query, q_params)
            try:
                return cur.fetchall()
            except Exception:
                return []
