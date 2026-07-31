"""Application-level constants, defaults, and feature flags.

These values are NOT loaded from the environment -- they are compile-time
constants or phase-gated feature flags.
"""

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
DEFAULT_CURRENCY: str = "INR"
DEFAULT_MAX_ITERATIONS: int = 10
DEFAULT_TEMPERATURE: float = 0.3
DEFAULT_MAX_RECOVERY_ATTEMPTS: int = 3

# ---------------------------------------------------------------------------
# Feature Flags  (toggled as phases are implemented)
# ---------------------------------------------------------------------------
ENABLE_REFLECTION: bool = True        # Phase 2
ENABLE_CRITIC: bool = True            # Phase 2
ENABLE_EXPLAINABILITY: bool = True    # Phase 2
ENABLE_HUMAN_APPROVAL: bool = True    # Phase 3
ENABLE_BOOKING: bool = True           # Phase 3
ENABLE_META_REASONING: bool = True    # Phase 3
ENABLE_MULTI_AGENT: bool = False      # Phase 3 (skeleton only)

# ---------------------------------------------------------------------------
# Simulation flags (for testing meta-reasoning)
# ---------------------------------------------------------------------------
SIMULATE_PAYMENT_FAILURE: bool = False
USE_MULTI_AGENT: bool = False

# ---------------------------------------------------------------------------
# Supported categories for sub-goals
# ---------------------------------------------------------------------------
SUB_GOAL_CATEGORIES: list[str] = [
    "travel",
    "accommodation",
    "transport",
    "food",
    "activities",
    "budget",
    "booking",
]

# ---------------------------------------------------------------------------
# Tool registry name -> module path  (used by capability_dispatcher)
# ---------------------------------------------------------------------------
TOOL_REGISTRY: dict[str, str] = {
    "search_flights": "tools.travel_research",
    "search_hotels": "tools.travel_research",
    "get_weather": "tools.weather",
    "check_constraints": "tools.constraint_checker",
    "load_preferences": "tools.memory",
    "book_flight": "tools.booking",
    "book_hotel": "tools.booking",
    "make_reservation": "tools.reservation",
    "process_payment": "tools.payment",
    "optimize_route": "tools.route_optimizer",
    "generate_alternatives": "tools.alternative_generator",
}
