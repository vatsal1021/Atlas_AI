"""Application-level constants, defaults, and feature flags."""

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
DEFAULT_CURRENCY: str = "INR"
DEFAULT_MAX_REACT_ITERATIONS: int = 8
DEFAULT_MAX_REFLECT_ITERATIONS: int = 3
DEFAULT_TEMPERATURE: float = 0.3
DEFAULT_TEMPERATURE_FAST: float = 0.0   # for IntentNode classification calls

# ---------------------------------------------------------------------------
# Feature Flags
# ---------------------------------------------------------------------------
ENABLE_CRITIC: bool = True              # run CriticGate / CriticNode
ENABLE_HUMAN_APPROVAL: bool = True      # interrupt for irreversible actions
ENABLE_MULTI_AGENT: bool = False        # multi-agent collaboration (future)

# ---------------------------------------------------------------------------
# Tools that require human approval before execution
# ---------------------------------------------------------------------------
IRREVERSIBLE_TOOLS: set[str] = {
    "book_flight",
    "book_hotel",
    "book_train",
    "make_reservation",
    "process_payment",
    "cancel_booking",
}

# ---------------------------------------------------------------------------
# CriticGate heuristics — trigger Critic when any of these are true
# ---------------------------------------------------------------------------
CRITIC_TRIGGER_TOOLS: set[str] = {
    "book_flight",
    "book_hotel",
    "book_train",
    "make_reservation",
    "process_payment",
    "cancel_booking",
}
CRITIC_REACT_ITERATION_THRESHOLD: int = 3   # ran ≥ this many ReAct steps

# ---------------------------------------------------------------------------
# Tool registry  name → module path  (used by ToolExecutionNode)
# ---------------------------------------------------------------------------
TOOL_REGISTRY: dict[str, str] = {
    # Research
    "search_flights":        "tools.travel_research",
    "search_hotels":         "tools.travel_research",
    "search_trains":         "tools.travel_research",
    "get_weather":           "tools.weather",
    "optimize_route":        "tools.route_optimizer",
    "generate_alternatives": "tools.alternative_generator",
    # Constraints & memory
    "check_constraints":     "tools.constraint_checker",
    "load_preferences":      "tools.memory",
    # Booking & payment
    "book_flight":           "tools.booking",
    "book_hotel":            "tools.booking",
    "book_train":            "tools.booking",
    "make_reservation":      "tools.reservation",
    "process_payment":       "tools.payment",
    "cancel_booking":        "tools.booking",
}
