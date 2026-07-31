"""Pydantic schemas for plan-related structures."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PlanStep(BaseModel):
    """A single step in an itinerary plan."""

    day: int = Field(description="Day number (1-indexed)")
    time_slot: str = Field(default="", description="morning | afternoon | evening | full_day")
    activity: str = Field(description="What to do")
    location: str = Field(default="", description="Where")
    estimated_cost: float = Field(default=0.0, description="Cost estimate")
    currency: str = Field(default="INR")
    notes: str = Field(default="")


class TripPlan(BaseModel):
    """A complete trip itinerary."""

    destination: str
    days: int
    total_budget: float
    currency: str = "INR"
    steps: list[PlanStep] = Field(default_factory=list)
    total_estimated_cost: float = 0.0
    warnings: list[str] = Field(default_factory=list)
