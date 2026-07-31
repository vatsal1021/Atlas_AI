"""Booking Specialist specialised agent."""

from __future__ import annotations

from agents.coordinator import Agent


class BookingSpecialistAgent(Agent):
    """Specialises in securing reservations and executing payments safely."""

    ROLE = "booking_specialist"
    SYSTEM_PROMPT = (
        "You are a Booking and Reservations Specialist. Ensure all flights, "
        "hotels, and activities are correctly reserved. Handle payment flows "
        "and recover gracefully from reservation failures."
    )

    def plan(self, state: dict) -> dict:
        """Stub for specialized booking logic."""
        return {}
