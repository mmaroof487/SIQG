"""AI-powered query generation and explanation endpoints.

Phase 6: Natural Language → SQL conversion and query explainer.
- NL→SQL: Convert user questions to SQL using LLM
- Explain: Generate plain English explanation of SQL queries
"""
from fastapi import APIRouter, Request, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
import httpx
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
- Always include a LIMIT clause for SELECT queries (max 1000).
- If the question is ambiguous or unsafe, return: ERROR: <reason>
- Use proper SQL syntax for PostgreSQL.
- Be conservative — if unsure, ask for clarification via ERROR response."""

SYSTEM_PROMPT_EXPLAIN = """You are a SQL expert. Explain what the given SQL query does in plain English.

RULES:
- Be concise (2-4 sentences maximum).
- Use simple language — assume the reader is non-technical.
- Describe what data is being retrieved or modified.
- Mention any filters, sorting, or aggregations applied.
- Do not include technical jargon without explanation."""


# ============================================================================
# AI Helper Functions
# ============================================================================

async def call_llm(system: str, user_message: str) -> str:
    """Call OpenAI API to generate SQL or explanation."""
    if not settings.ai_enabled or not settings.openai_api_key:
        logger.warning("AI features disabled or API key not configured")
        return "AI features are currently disabled."

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
                    "temperature": 0.1,  # Low temp for deterministic SQL
                },
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()
            logger.debug(f"LLM response: {content[:100]}...")
            return content
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        return f"ERROR: {str(e)}"


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

        # Build prompt
        prompt = f"Question: {body.question}"
        if body.schema_hint:
            prompt += f"\nDatabase schema: {body.schema_hint}"

        # Call LLM
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
        logger.warning(f"[{trace_id}] NL→SQL pipeline error: {e.detail}")
        return NLResponse(
            original_question=body.question,
            generated_sql="",
            status="error",
            message=f"Pipeline error: {e.detail}",
        )
    except Exception as e:
        logger.error(f"[{trace_id}] NL→SQL unexpected error: {e}")
        return NLResponse(
            original_question=body.question,
            generated_sql="",
            status="error",
            message=f"Unexpected error: {str(e)}",
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
