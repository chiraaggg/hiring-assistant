from langchain.tools import Tool
from typing import Dict, Any, List
from .db import run_query, run_query_one
from .groq_llm import GroqLLM
from .config import settings
import json

# ---- DB Tools: they are async functions but LangChain Tool expects sync callable.
# We'll expose sync wrappers that call the async DB functions via asyncio.run in a thread.
import asyncio
def run_async(coro):
    return asyncio.get_event_loop().run_until_complete(coro)

# --- Tool implementations ---

async def _get_candidate_by_id_async(candidate_id: int) -> Dict[str, Any]:
    sql = """
    SELECT c.*, r.resume_text, r.summary as resume_summary
    FROM candidates c
    LEFT JOIN resumes r ON r.search_id = c.search_id
    WHERE c.id = $1
    LIMIT 1;
    """
    return await run_query_one(sql, candidate_id)

def get_candidate_by_id_tool(input_str: str) -> str:
    """
    input_str: candidate id as string or json {"id": 123}
    returns JSON string of candidate record
    """
    try:
        parsed = json.loads(input_str)
        cid = parsed.get("id") if isinstance(parsed, dict) else None
    except Exception:
        cid = None
    if cid is None:
        try:
            cid = int(input_str.strip())
        except Exception as e:
            return json.dumps({"error": "invalid candidate id", "detail": str(e)})
    row = run_async(_get_candidate_by_id_async(cid))
    return json.dumps(row, default=str)

async def _search_candidates_async(filters: Dict[str, Any], limit: int = 25) -> List[Dict[str, Any]]:
    # build SQL similar to previous version but parameterized
    clauses = []
    params = []
    i = 1
    if filters.get("skills"):
        clauses.append(f"skills ILIKE '%' || ${i} || '%'")
        params.append(filters["skills"])
        i +=1
    if filters.get("min_exp"):
        clauses.append(f"COALESCE(NULLIF(total_experience, ''), '0')::numeric >= ${i}")
        params.append(filters["min_exp"])
        i +=1
    if filters.get("name"):
        clauses.append(f"name ILIKE '%' || ${i} || '%'")
        params.append(filters["name"])
        i +=1
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    sql = f"""
    SELECT c.id, c.name, c.email, c.phone, c.skills, c.total_experience, c.relevant_work_experience, c.summary, c.call_status, c.updated_at
    FROM candidates c
    {where}
    ORDER BY c.updated_at DESC
    LIMIT {limit};
    """
    return await run_query(sql, *params)

def search_candidates_tool(input_str: str) -> str:
    """
    input_str: json string of filters, e.g. {"skills": "python, django", "min_exp": 3}
    returns JSON string list of candidates
    """
    try:
        filters = json.loads(input_str)
        if not isinstance(filters, dict):
            return json.dumps({"error": "filters must be a JSON object"})
    except Exception:
        return json.dumps({"error": "invalid JSON filters"})
    rows = run_async(_search_candidates_async(filters))
    return json.dumps(rows, default=str)

async def _fetch_pipeline_metrics_async(days: int = 90):
    sql = """
    SELECT stage, COUNT(*) as cnt
    FROM candidate_pipeline
    WHERE updated_at >= (now() - interval '{} days')
    GROUP BY stage;
    """.format(days)
    rows = await run_query(sql)
    return rows

def fetch_pipeline_metrics_tool(input_str: str) -> str:
    """
    input_str: optional days as integer or json {"days": 90}
    returns JSON metrics
    """
    days = 90
    try:
        parsed = json.loads(input_str)
        if isinstance(parsed, dict) and parsed.get("days"):
            days = int(parsed.get("days"))
    except Exception:
        try:
            days = int(input_str)
        except Exception:
            days = 90
    rows = run_async(_fetch_pipeline_metrics_async(days))
    return json.dumps(rows, default=str)

# --- Generation tools using GroqLLM ---

# create a Groq LLM instance
groq_llm = GroqLLM()

def jd_generator_tool(input_str: str) -> str:
    """
    input_str: json string with job_context: {"title":"Senior Backend", "skills":"python,aws", "seniority":"Senior", "location":"Bengaluru", "noc":2}
    returns: JSON string with fields: short_jd, full_jd, must_haves, headlines
    """
    try:
        ctx = json.loads(input_str)
    except Exception:
        ctx = {"raw": input_str}
    prompt = f"""
You are a professional JD writer.

Context: {json.dumps(ctx)}

Write output as JSON with keys:
- short_jd (one paragraph)
- full_jd (sections: About the team, Responsibilities, Required skills, Nice to have, Perks)
- must_haves (array of 3 strings)
- headlines (array of 3 strings)

Be concise and use neutral professional tone.
"""
    out = groq_llm._call(prompt, None)
    # Try to extract JSON from LLM output, else return raw string
    try:
        # LLM may return JSON blob in text — try to find first "{" and parse
        start = out.find("{")
        if start != -1:
            json_part = out[start:]
            parsed = json.loads(json_part)
            return json.dumps(parsed, default=str)
    except Exception:
        pass
    return json.dumps({"raw": out})

def email_generator_tool(input_str: str) -> str:
    """
    input_str: json {"candidate": {...}, "role": {...}, "tone":"friendly"}
    returns JSON string with subject_a, subject_b, short_email, long_email, personalization_hooks
    """
    try:
        ctx = json.loads(input_str)
    except Exception:
        ctx = {"raw": input_str}
    prompt = f"""
Write outreach emails for a candidate.

Context: {json.dumps(ctx)}

Return JSON:
- subject_a, subject_b
- short_email
- long_email
- personalization_hooks (array of 2)
"""
    out = groq_llm._call(prompt, None)
    try:
        start = out.find("{")
        if start != -1:
            parsed = json.loads(out[start:])
            return json.dumps(parsed, default=str)
    except Exception:
        pass
    return json.dumps({"raw": out})

# --- Web search placeholder ---
def web_search_tool(input_str: str) -> str:
    """
    Placeholder tool: input is query string. Returns short synthesized result and list of sources.
    Replace with real SERP / Bing / Tavily integration.
    """
    # For now, just echo request; LangChain-driven agent can call this.
    return json.dumps({"query": input_str, "note": "web search not implemented. Connect a search API."})

# --- Wrap into LangChain Tool objects ---
tool_get_candidate = Tool.from_function(
    func=get_candidate_by_id_tool,
    name="get_candidate_by_id",
    description="Get candidate by id. Input: integer id or JSON {\"id\":123}. Returns candidate record as JSON."
)

tool_search_candidates = Tool.from_function(
    func=search_candidates_tool,
    name="search_candidates",
    description="Search candidates using filters provided as JSON. Example: {\"skills\":\"python,django\",\"min_exp\":3}. Returns array of candidate JSON objects."
)

tool_fetch_metrics = Tool.from_function(
    func=fetch_pipeline_metrics_tool,
    name="fetch_pipeline_metrics",
    description="Fetch pipeline metrics. Input: optional days integer or JSON {\"days\":90}."
)

tool_jd_generator = Tool.from_function(
    func=jd_generator_tool,
    name="jd_generator",
    description="Generate job description. Input JSON with job context. Returns JSON with short_jd, full_jd, must_haves, headlines."
)

tool_email_generator = Tool.from_function(
    func=email_generator_tool,
    name="email_generator",
    description="Generate outreach emails. Input JSON {\"candidate\": {...}, \"role\": {...}, \"tone\":\"friendly\"}."
)

tool_web_search = Tool.from_function(
    func=web_search_tool,
    name="web_search",
    description="Placeholder web search tool. Input: query string. Returns JSON with quick answer and sources (if implemented)."
)

ALL_TOOLS = [
    tool_get_candidate,
    tool_search_candidates,
    tool_fetch_metrics,
    tool_jd_generator,
    tool_email_generator,
    tool_web_search
]
