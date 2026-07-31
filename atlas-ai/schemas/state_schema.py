"""Pydantic schemas for state objects used throughout the graph.

These models provide validation and serialisation for the structured data
that flows through TripState.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ParsedGoal(BaseModel):
    """Structured representation of a user's travel goal."""

    destination: str = Field(description="Target destination city/country")
    budget: float = Field(description="Total budget amount")
    currency: str = Field(default="INR", description="Budget currency code")
    days: int = Field(description="Trip duration in days")
    start_date: str = Field(default="", description="ISO-format start date (may be empty)")
    end_date: str = Field(default="", description="ISO-format end date (may be empty)")
    travelers: int = Field(default=1, description="Number of travellers")
    preferences: list[str] = Field(default_factory=list, description="User preferences")
    constraints: list[str] = Field(default_factory=list, description="Hard constraints")
    inferred_fields: list[str] = Field(
        default_factory=list,
        description="Fields whose values were inferred rather than stated",
    )


class SubGoal(BaseModel):
    """A decomposed sub-objective for the trip."""

    id: str = Field(description="Unique sub-goal identifier, e.g. sg-1")
    category: str = Field(
        description="Category: travel | accommodation | transport | food | activities | budget | booking"
    )
    description: str = Field(description="Human-readable description")
    dependencies: list[str] = Field(
        default_factory=list,
        description="IDs of sub-goals this depends on",
    )
    status: str = Field(
        default="pending",
        description="pending | in_progress | completed | failed",
    )
    priority: int = Field(default=3, ge=1, le=5, description="1 (highest) to 5 (lowest)")


class PlannedAction(BaseModel):
    """A single action the planner wants to execute."""

    tool: str = Field(description="Tool function name to invoke")
    parameters: dict = Field(default_factory=dict, description="Tool call arguments")
    reasoning: str = Field(default="", description="Why this action was chosen")
    sub_goal_id: str = Field(default="", description="Which sub-goal this serves")


class WorldFact(BaseModel):
    """A derived fact produced by the world-model node."""

    id: str = Field(description="Unique fact identifier, e.g. wf-1")
    category: str = Field(description="Fact category (weather, flights, hotels, activities, etc.)")
    statement: str = Field(description="Human-readable fact statement")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence 0-1")
    source_tool: str = Field(default="", description="Tool that produced the evidence")
    implications: list[str] = Field(
        default_factory=list,
        description="What this fact implies for planning",
    )


class SubGoalStatus(BaseModel):
    """Evaluation result for a single sub-goal."""

    satisfied: bool = Field(description="Whether this sub-goal is met")
    reasoning: str = Field(default="", description="Explanation")


class GoalEvaluation(BaseModel):
    """Complete evaluation output from the goal_evaluator node."""

    sub_goal_statuses: dict[str, SubGoalStatus] = Field(
        default_factory=dict,
        description="Keyed by sub-goal id",
    )
    all_satisfied: bool = Field(default=False)
    summary: str = Field(default="")
