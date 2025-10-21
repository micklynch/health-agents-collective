"""FHIR search planning utilities powered by an LLM.

This module asks the model to interpret a natural language query and produce
well-formed FHIR search terms so downstream tools can stay simple.
"""

from __future__ import annotations

import asyncio
import re
from typing import List, Optional

from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel

from src.core.config import settings


class ConditionSearchPlan(BaseModel):
    """Structured output describing a FHIR condition search plan."""

    resource_type: str = Field(
        default="Condition",
        description="FHIR resource type the search should target.",
    )
    search_terms: List[str] = Field(
        default_factory=list,
        description="Ordered list of search keywords or phrases to try.",
    )
    notes: Optional[str] = Field(
        default=None,
        description="Optional free-text guidance for the caller.",
    )


_PLANNER_AGENT: Optional[Agent] = None


def _ensure_planner_agent() -> Optional[Agent]:
    """Create the planner agent lazily when configuration allows it."""

    global _PLANNER_AGENT

    if not settings.open_router_api_key:
        return None

    if _PLANNER_AGENT is not None:
        return _PLANNER_AGENT

    client = AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=settings.open_router_api_key,
    )

    model = OpenAIModel(settings.open_router_model, client=client)

    planner = Agent(
        model=model,
        name="fhir_condition_search_planner",
        result_type=ConditionSearchPlan,
    )

    @planner.system_prompt
    def _system_prompt(_) -> str:  # pragma: no cover - prompt text only
        return (
            "You are a clinical terminology assistant that prepares search plans "
            "for querying FHIR Condition resources. Given a natural language "
            "request, respond with a JSON plan containing the resource type and "
            "a concise list of search terms (max 5) that will retrieve matching "
            "conditions. Include abbreviations or common synonyms when helpful. "
            "Default the resource type to 'Condition' unless the user clearly "
            "asks for a different FHIR resource. Do not explain the plan; only "
            "return the structured data."
        )

    _PLANNER_AGENT = planner
    return _PLANNER_AGENT


def _heuristic_terms(condition_text: str) -> List[str]:
    """Fallback tokenization strategy when the planner is unavailable."""

    seen: set[str] = set()
    terms: List[str] = []

    def add(term: str) -> None:
        normalized = term.strip()
        if not normalized:
            return
        lowered = normalized.lower()
        if lowered in seen:
            return
        seen.add(lowered)
        terms.append(normalized)

    add(condition_text)

    # Remove parenthetical content and add its parts separately, e.g. "DM".
    for match in re.findall(r"\(([^)]+)\)", condition_text):
        add(match)

    without_parens = re.sub(r"\([^)]*\)", " ", condition_text)
    if without_parens != condition_text:
        add(without_parens)

    tokens = [token for token in re.split(r"[\s,/]+", without_parens) if token]

    # Add decreasing n-grams and individual tokens.
    for length in range(len(tokens), 0, -1):
        add(" ".join(tokens[:length]))

    for token in tokens:
        add(token)

    return terms[:5] or [condition_text]


def _dedupe_terms(terms: List[str]) -> List[str]:
    seen: set[str] = set()
    ordered: List[str] = []
    for term in terms:
        normalized = term.strip()
        if not normalized:
            continue
        lowered = normalized.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        ordered.append(normalized)
    return ordered


async def plan_condition_search(condition_text: str) -> ConditionSearchPlan:
    """Return a structured search plan, falling back to heuristics when needed."""

    agent = _ensure_planner_agent()
    if agent is None:
        return ConditionSearchPlan(
            search_terms=_heuristic_terms(condition_text),
            notes="Planner disabled: OPENROUTER_API_KEY not configured.",
        )

    try:
        result = await agent.run(condition_text)
    except Exception as exc:  # pragma: no cover - network/runtime failures
        return ConditionSearchPlan(
            search_terms=_heuristic_terms(condition_text),
            notes=f"Planner failed: {exc}",
        )

    plan = result.output
    if plan.resource_type.lower() != "condition":
        plan.resource_type = "Condition"

    plan.search_terms = _dedupe_terms(plan.search_terms) or _heuristic_terms(condition_text)
    return plan


def plan_condition_search_sync(condition_text: str) -> ConditionSearchPlan:
    """Synchronous helper for contexts outside of async loops (e.g. tests)."""

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        raise RuntimeError("plan_condition_search_sync cannot be called from a running event loop")

    return asyncio.run(plan_condition_search(condition_text))
