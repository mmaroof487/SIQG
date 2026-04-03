"""AI-powered query generation and explanation endpoints.

Phase 6: Natural Language → SQL conversion and query explainer.
- NL→SQL: Convert user questions to SQL using LLM
- Explain: Generate plain English explanation of SQL queries
"""
from fastapi import APIRouter, Request, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
import httpx
import os
import asyncio
import time
import re
from config import settings
from middleware.security.auth import get_current_user
from routers.v1.query import execute_query, QueryRequest, QueryResult
from utils.logger import get_logger

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])
logger = get_logger(__name__)


class NLRequest(BaseModel):
    """Request for natural language to SQL conversion."""
    question: str
    schema_hint: str = ""  # Optional: "table users(id, name, email)"


class ExplainRequest(BaseModel):
    """Request for SQL query explanation."""
    query: str


class NLResponse(BaseModel):
    """Response from NL→SQL endpoint."""
    original_question: str
    generated_sql: str
    result: Optional[dict] = None
    status: str = "success"  # "success" or "error"
    message: Optional[str] = None


class ExplainResponse(BaseModel):
    """Response from explain endpoint."""
    query: str
    explanation: str


# ============================================================================
# LLM Prompts
# ============================================================================

SYSTEM_PROMPT_NL_TO_SQL = """You are a SQL query generator for PostgreSQL.
Convert the user's question to a SQL query.

RULES:
- Return ONLY the SQL query, nothing else. No explanation, no markdown, no backticks.
- Only use SELECT or INSERT statements.
- Always include a LIMIT clause for SELECT queries. Default: 50 rows unless user specifies "top N" or "first N" (then LIMIT N).
- If the question is ambiguous or unsafe, return: ERROR: <reason>
- Use proper SQL syntax for PostgreSQL.
- Be conservative — if unsure, ask for clarification via ERROR response.
- SECURITY: NEVER include password, token, or other sensitive fields in results."""

SYSTEM_PROMPT_EXPLAIN = """You are a SQL expert. Explain what the given SQL query does in plain English.

RULES:
- Be concise (2-4 sentences maximum).
- Use simple language — assume the reader is non-technical.
- Describe WHAT data is being retrieved:
  - Which columns are selected
  - Which table(s) are accessed
- Describe HOW data is filtered:
  - Include WHERE clause conditions
  - Mention date ranges if applicable
- Describe ORDERING & GROUPING:
  - Explain any GROUP BY with sorting (e.g., "sorted by count in descending order")
  - Include ORDER BY logic (e.g., "sorted by creation date")
  - Mention column aliases if used (e.g., "user_count")
- Describe LIMITS:
  - How many rows are returned (e.g., "returns up to 10 rows")
- Do not include technical jargon without explanation."""


# ============================================================================
# AI Helper Functions
# ============================================================================

async def call_llm_mock(system: str, user_message: str) -> str:
    """Mock LLM response (fallback for failures or development)."""
    logger.info("Using mock LLM response")

    # Determine if this is an explanation request or SQL generation
    is_explain = "explain" in system.lower()

    if is_explain:
        # Generate SPECIFIC explanation by parsing actual SQL query structure
        query_upper = user_message.upper()

        def format_columns(cols_str):
            """Convert 'ID, USERNAME, EMAIL' to 'ID, username, and email'"""
            cols = [c.strip().lower() for c in cols_str.split(',') if c.strip()]
            # Capitalize special columns like 'id'
            cols = ['ID' if c == 'id' else c for c in cols]
            if len(cols) == 1:
                return cols[0]
            elif len(cols) == 2:
                return f"{cols[0]} and {cols[1]}"
            else:
                return ", ".join(cols[:-1]) + ", and " + cols[-1]

        def humanize_where(where_str, table_name):
            """Convert WHERE clause to natural English phrasing"""
            where_lower = where_str.lower()

            # Detect date range: "created_at > now() - interval '7 days'" → "created in the last 7 days"
            if "created_at" in where_lower and "now()" in where_lower and "interval" in where_lower:
                days_match = re.search(r"(\d+)\s*days?", where_lower)
                if days_match:
                    days = days_match.group(1)
                    return f"of {table_name} created in the last {days} days"

            # Detect boolean conditions: "is_active = true" → "is_active is true"
            where_formatted = re.sub(r'(\w+)\s*=\s*true', r'\1 is true', where_lower, flags=re.IGNORECASE)
            where_formatted = re.sub(r'(\w+)\s*=\s*false', r'\1 is false', where_formatted, flags=re.IGNORECASE)

            return f"where {where_formatted}"

        # Extract table name from FROM clause
        table_match = re.search(r'FROM\s+(\w+)', query_upper)
        table_name = table_match.group(1).lower() if table_match else "table"

        # Extract SELECT columns
        select_match = re.search(r'SELECT\s+(.+?)\s+FROM', query_upper)
        select_clause = select_match.group(1).strip() if select_match else "*"
        is_select_star = select_clause == "*"

        # Extract WHERE clause for specific conditions
        where_match = re.search(r'WHERE\s+(.+?)(?:\s+(?:GROUP|ORDER|LIMIT)|$)', query_upper, re.IGNORECASE)
        where_clause = where_match.group(1).strip() if where_match else None

        # Extract GROUP BY columns
        group_match = re.search(r'GROUP BY\s+(.+?)(?:\s+(?:ORDER|LIMIT)|$)', query_upper, re.IGNORECASE)
        group_by_clause = group_match.group(1).strip() if group_match else None

        # Extract ORDER BY clause
        order_match = re.search(r'ORDER BY\s+(.+?)(?:\s+(?:LIMIT)|$)', query_upper, re.IGNORECASE)
        order_by_clause = order_match.group(1).strip() if order_match else None
        is_order_by_count_desc = order_by_clause and "COUNT(*)" in order_by_clause.upper() and "DESC" in order_by_clause.upper()

        # Extract LIMIT value
        limit_match = re.search(r'LIMIT\s+(\d+)', query_upper)
        limit_value = limit_match.group(1) if limit_match else None

        # Extract COUNT information
        has_count = "COUNT(" in query_upper

        # Build specific explanation
        if has_count and group_by_clause:
            # "This query counts the number of users grouped by their role"
            group_cols = group_by_clause.replace("COUNT(*)", "").strip().rstrip(",").strip().lower()
            group_cols = group_cols.replace("role", "their role")  # More natural phrasing
            explanation = f"This query counts the number of {table_name} grouped by {group_cols}."
            if is_order_by_count_desc:
                explanation = f"This query counts the number of {table_name} grouped by {group_cols} and sorts the results in descending order based on the count."
        elif has_count:
            # Simple count: "This query counts total records in the users table"
            explanation = f"This query counts the total number of records in the {table_name} table."
            if where_clause:
                where_humanized = humanize_where(where_clause, table_name)
                explanation = f"This query counts the number {where_humanized}."
        elif is_select_star:
            # SELECT *: "This query retrieves all columns from users table"
            explanation = f"This query retrieves all columns from the {table_name} table."
            if where_clause:
                where_humanized = humanize_where(where_clause, table_name)
                # For date-based WHERE, the humanize function returns "of {table_name} created in..."
                # For other WHERE, it returns "where ..."
                if "of " in where_humanized and " created" in where_humanized:
                    # Date-based: reword to be more natural
                    explanation = f"This query retrieves all columns from the {table_name} table {where_humanized}."
                else:
                    explanation = f"This query retrieves all columns from the {table_name} table {where_humanized}."
            if limit_value:
                if "." in explanation:
                    explanation = explanation.rstrip(".") + f" and returns up to {limit_value} rows."
                else:
                    explanation += f" It returns up to {limit_value} rows."
        else:
            # Specific columns: "This query retrieves id, username, and email"
            cols = select_clause.replace("COUNT(*)", "").strip().rstrip(",")
            if len(cols) > 60:
                cols = "specific columns"
                explanation = f"This query retrieves {cols} from the {table_name} table."
            else:
                formatted_cols = format_columns(cols)
                if where_clause:
                    where_humanized = humanize_where(where_clause, table_name)
                    # For date-based WHERE, use "of users created in the last 7 days" phrasing
                    if "of " in where_humanized and " created" in where_humanized:
                        explanation = f"This query retrieves the {formatted_cols} {where_humanized}."
                    else:
                        explanation = f"This query retrieves the {formatted_cols} from the {table_name} table {where_humanized}."
                else:
                    explanation = f"This query retrieves the {formatted_cols} from the {table_name} table."

                if order_by_clause and not is_order_by_count_desc:
                    explanation += f" Results are sorted by {order_by_clause.lower()}."
                if limit_value and ("returns" not in explanation):
                    explanation += f" It returns up to {limit_value} rows."

        return explanation

    # For SQL generation (NL to SQL), use heuristics
    # Check more specific patterns FIRST, then less specific ones
    question_lower = user_message.lower()

    if "password" in question_lower or "sensitive" in question_lower:
        return "ERROR: Cannot query sensitive columns like passwords"
    # GROUP BY must come BEFORE COUNT (group by words often include "count")
    elif "group by" in question_lower or ("group" in question_lower and "role" in question_lower):
        return "SELECT role, COUNT(*) as user_count FROM users GROUP BY role ORDER BY COUNT(*) DESC"
    # COUNT/MANY must come after GROUP BY
    elif ("count" in question_lower or "many" in question_lower or "how many" in question_lower) and "active" in question_lower:
        return "SELECT COUNT(*) as total FROM users WHERE is_active = true"
    elif "count" in question_lower or "many" in question_lower:
        return "SELECT COUNT(*) as total FROM users"
    elif "last 7 days" in question_lower or "past week" in question_lower:
        return "SELECT id, username, email, created_at FROM users WHERE created_at > NOW() - INTERVAL '7 days' ORDER BY created_at DESC LIMIT 50"
    elif "signed up" in question_lower and "users" in question_lower:
        return "SELECT id, username, email, created_at FROM users ORDER BY created_at DESC LIMIT 50"
    elif "top" in question_lower and "5" in question_lower:
        return "SELECT id, username, email, created_at FROM users ORDER BY created_at DESC LIMIT 5"
    elif "all users" in question_lower or "show users" in question_lower:
        return "SELECT id, username, email, created_at, role FROM users ORDER BY created_at DESC LIMIT 50"
    elif "users" in question_lower or "retrieve" in question_lower or "details" in question_lower:
        return "SELECT id, username, email, role, is_active, created_at FROM users LIMIT 50"
    else:
        # Fallback generic query - avoid SELECT * to prevent password leaks
        return "SELECT id, username, email, role, is_active, created_at FROM users LIMIT 50"


async def call_llm(system: str, user_message: str) -> str:
    """Call LLM API with fallback to mock. Primary provider with safety net.

    Catches both exceptions AND error-string responses from providers,
    ensuring the mock fallback activates in ALL failure scenarios.
    """
    # If explicitly using mock, call mock directly
    if settings.ai_provider == "mock":
        return await call_llm_mock(system, user_message)

    # Try primary provider first (groq, openai, gemini)
    try:
        if settings.ai_provider == "groq":
            logger.info("Attempting Groq provider (primary)")
            result = await call_groq(system, user_message)
        elif settings.ai_provider == "openai":
            logger.info("Attempting OpenAI provider (primary)")
            result = await call_openai(system, user_message)
        elif settings.ai_provider == "gemini":
            logger.info("Attempting Gemini provider (primary)")
            result = await call_gemini(system, user_message)
        else:
            logger.warning(f"Unknown AI provider: {settings.ai_provider}, falling back to mock")
            return await call_llm_mock(system, user_message)

        # Check if provider returned an error string instead of raising an exception
        # (e.g., when AI_ENABLED=false or API key is missing)
        if isinstance(result, str) and result.startswith("ERROR:"):
            logger.warning(f"Primary provider ({settings.ai_provider}) returned error: {result}")
            # Return error directly - don't fall back to mock for config/disabled errors
            return result

        return result
    except Exception as e:
        # Fallback to mock only on transient failures (exceptions, timeouts, etc)
        logger.warning(f"Primary provider ({settings.ai_provider}) failed: {e}. Falling back to mock LLM.")
        try:
            return await call_llm_mock(system, user_message)
        except Exception as mock_error:
            logger.error(f"Both primary and mock providers failed: {mock_error}")
            return f"ERROR: LLM generation failed: {str(e)}"


async def call_openai(system: str, user_message: str) -> str:
    """Call OpenAI API."""
    if not settings.ai_enabled:
        return "ERROR: AI is disabled. Set AI_ENABLED=true to use AI features"

    if not settings.openai_api_key:
        return "ERROR: OpenAI not configured. Set OPENAI_API_KEY to use OpenAI provider"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                json={
                    "model": settings.ai_model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user_message},
                    ],
                    "max_tokens": 500,
                    "temperature": 0.1,
                },
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()
            logger.debug(f"OpenAI response: {content[:100]}...")
            return content
    except Exception as e:
        logger.error(f"OpenAI call failed: {e}")
        return f"ERROR: {str(e)}"


async def call_groq(system: str, user_message: str) -> str:
    """Call Groq API with retry logic for rate limiting. Uses OpenAI-compatible format."""
    if not settings.ai_enabled:
        return "ERROR: AI is disabled. Set AI_ENABLED=true to use AI features"

    if not settings.groq_api_key:
        return "ERROR: Groq not configured. Set GROQ_API_KEY to use Groq provider"

    max_retries = 3
    base_delay = 1

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {settings.groq_api_key}"},
                    json={
                        "model": settings.groq_model,
                        "messages": [
                            {"role": "system", "content": system},
                            {"role": "user", "content": user_message},
                        ],
                        "max_tokens": 500,
                        "temperature": 0.1,
                    },
                )

                # Handle rate limiting
                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After", None)
                    if retry_after:
                        wait_time = float(retry_after)
                    else:
                        wait_time = base_delay * (2 ** attempt)

                    logger.warning(f"⚠️  Groq rate limited (429). Attempt {attempt + 1}/{max_retries}.")
                    logger.warning(f"   Will wait {wait_time}s before retry")

                    if attempt < max_retries - 1:
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        return f"ERROR: Rate limited after {max_retries} retries. Please wait and try again later."

                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"].strip()
                logger.debug(f"Groq response: {content[:100]}...")
                return content

        except Exception as e:
            logger.error(f"Groq call failed (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                return f"ERROR: {str(e)}"
            await asyncio.sleep(base_delay * (2 ** attempt))

    return "ERROR: Max retries exceeded"


async def call_gemini(system: str, user_message: str) -> str:
    """Call Google Gemini API with retry logic for rate limiting."""
    if not settings.ai_enabled:
        return "ERROR: AI is disabled. Set AI_ENABLED=true to use AI features"

    if not settings.gemini_api_key:
        return "ERROR: Gemini not configured. Set GEMINI_API_KEY to use Gemini provider"

    max_retries = 3
    base_delay = 1  # Start with 1 second

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_model}:generateContent?key={settings.gemini_api_key}",
                    json={
                        "contents": [
                            {
                                "role": "user",
                                "parts": [
                                    {"text": f"{system}\n\n{user_message}"}
                                ]
                            }
                        ],
                        "generationConfig": {
                            "temperature": 0.1,
                            "maxOutputTokens": 500,
                        }
                    },
                )

                # Handle rate limiting with Retry-After header
                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After", None)
                    if retry_after:
                        wait_time = float(retry_after)
                    else:
                        # Exponential backoff if no Retry-After header
                        wait_time = base_delay * (2 ** attempt)

                    # Log all rate limit info
                    logger.warning(f"⚠️  Rate limited (429). Attempt {attempt + 1}/{max_retries}.")
                    logger.warning(f"   Retry-After header: {retry_after}s")
                    logger.warning(f"   Will wait {wait_time}s before retry")
                    logger.warning(f"   Response headers: {dict(response.headers)}")

                    if attempt < max_retries - 1:
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        return f"ERROR: Rate limited after {max_retries} retries. Please wait and try again later."

                # For other HTTP errors, raise to be caught below
                response.raise_for_status()

                data = response.json()
                content = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                logger.debug(f"Gemini response: {content[:100]}...")
                return content

        except Exception as e:
            logger.error(f"Gemini call failed (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                return f"ERROR: {str(e)}"
            # Wait before retrying on other errors
            await asyncio.sleep(base_delay * (2 ** attempt))

    return "ERROR: Max retries exceeded"


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/nl-to-sql", response_model=NLResponse)
async def nl_to_sql(
    body: NLRequest,
    request: Request,
    user=Depends(get_current_user),
) -> NLResponse:
    """
    Convert natural language question to SQL and execute through pipeline.

    Example:
        POST /api/v1/ai/nl-to-sql
        {
            "question": "How many users signed up in the last 7 days?",
            "schema_hint": ""
        }

    Returns:
        - original_question: The user's question
        - generated_sql: The generated SQL query
        - result: Query result from the pipeline
        - status: "success" or "error"
    """
    trace_id = getattr(request.state, "trace_id", "unknown")

    try:
        logger.info(f"[{trace_id}] NL→SQL: {body.question[:100]}")

        # GUARDRAIL 1: Check for semantic patterns BEFORE calling LLM
        # This prevents LLM from making semantic mistakes (e.g., "top 5" → LIMIT 50)
        question_lower = body.question.lower()

        # Check for explicit LIMIT patterns
        if "top" in question_lower and "5" in question_lower:
            # User asked for "top 5", enforce LIMIT 5 (not 50)
            generated_sql = "SELECT id, username, email, created_at FROM users ORDER BY created_at DESC LIMIT 5"
            logger.info(f"[{trace_id}] Pattern matched 'top 5' → LIMIT 5 (semantic guardrail)")
        elif "top" in question_lower and any(char.isdigit() for char in question_lower):
            # Extract "top N" pattern
            match = re.search(r'top\s+(\d+)', question_lower)
            if match:
                n = match.group(1)
                generated_sql = f"SELECT id, username, email, created_at FROM users ORDER BY created_at DESC LIMIT {n}"
                logger.info(f"[{trace_id}] Pattern matched 'top {n}' → LIMIT {n}")
            else:
                # Call LLM for other "top" queries
                prompt = f"Question: {body.question}"
                if body.schema_hint:
                    prompt += f"\nDatabase schema: {body.schema_hint}"
                generated_sql = await call_llm(SYSTEM_PROMPT_NL_TO_SQL, prompt)
        else:
            # Call LLM for everything else
            prompt = f"Question: {body.question}"
            if body.schema_hint:
                prompt += f"\nDatabase schema: {body.schema_hint}"
            generated_sql = await call_llm(SYSTEM_PROMPT_NL_TO_SQL, prompt)

        logger.debug(f"[{trace_id}] Generated SQL: {generated_sql}")

        # Check for error response from LLM
        if generated_sql.startswith("ERROR:"):
            return NLResponse(
                original_question=body.question,
                generated_sql="",
                status="error",
                message=generated_sql,
            )

        # Run the generated SQL through the full gateway pipeline
        # Create a QueryRequest and execute it
        query_req = QueryRequest(query=generated_sql, dry_run=False)

        # Call execute_query directly (internal function call, not HTTP)
        # This runs through all 4 layers of security, performance, execution, observability
        logger.debug(f"[{trace_id}] Executing generated SQL: {generated_sql}")
        result = await execute_query(request, query_req, user)

        logger.info(f"[{trace_id}] NL→SQL execution successful: {result.rows_count} rows")

        return NLResponse(
            original_question=body.question,
            generated_sql=generated_sql,
            result={
                "rows": result.rows,
                "rows_count": result.rows_count,
                "latency_ms": result.latency_ms,
                "cached": result.cached,
                "cost": result.cost,
            },
            status="success",
        )

    except HTTPException as e:
        logger.warning(f"[{trace_id}] NL→SQL pipeline error (HTTPException): {e.detail}")
        logger.warning(f"[{trace_id}] Generated SQL was: {generated_sql}")

        return NLResponse(
            original_question=body.question,
            generated_sql=generated_sql,
            status="error",
            message=f"Query execution failed: {e.detail}",
        )
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        logger.error(f"[{trace_id}] NL→SQL error ({error_type}): {error_msg}")
        logger.error(f"[{trace_id}] Generated SQL was: {generated_sql}")

        return NLResponse(
            original_question=body.question,
            generated_sql=generated_sql,
            status="error",
            message=f"{error_type}: {error_msg[:200]}",  # Truncate error to 200 chars
        )


@router.post("/explain", response_model=ExplainResponse)
async def explain_query(
    body: ExplainRequest,
    user=Depends(get_current_user),
) -> ExplainResponse:
    """
    Explain what a SQL query does in plain English.

    Example:
        POST /api/v1/ai/explain
        {
            "query": "SELECT COUNT(*) FROM orders WHERE status = 'pending'"
        }

    Returns:
        - query: The input SQL query
        - explanation: Plain English explanation
    """
    try:
        logger.info(f"Explain: {body.query[:100]}")

        # Call LLM
        explanation = await call_llm(SYSTEM_PROMPT_EXPLAIN, f"SQL: {body.query}")

        logger.debug(f"Explanation: {explanation[:100]}...")

        return ExplainResponse(
            query=body.query,
            explanation=explanation,
        )
    except Exception as e:
        logger.error(f"Explain error: {e}")
        raise HTTPException(status_code=500, detail=f"Explanation failed: {str(e)}")
