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
# Canonical Tool Name Map — maps aliases to single canonical names
# ---------------------------------------------------------------------------
CANONICAL_TOOL_MAP: dict[str, str] = {
    # Research
    "hotel_search":          "search_hotels",
    "hotels_search":         "search_hotels",
    "search_hotel":          "search_hotels",
    "flight_search":         "search_flights",
    "flights_search":        "search_flights",
    "search_flight":         "search_flights",
    "train_search":          "search_trains",
    "trains_search":         "search_trains",
    "search_train":          "search_trains",
    # Booking & Payment
    "hotel_booking":         "book_hotel",
    "flight_booking":        "book_flight",
    "train_booking":         "book_train",
    "payment":               "process_payment",
}


def get_canonical_tool_name(tool_name: str) -> str:
    """Return the canonical tool name for any tool or alias."""
    clean = tool_name.strip().lower()
    return CANONICAL_TOOL_MAP.get(clean, clean)


# ---------------------------------------------------------------------------
# Tool registry  name → module path  (used by ToolExecutionNode)
# ---------------------------------------------------------------------------
TOOL_REGISTRY: dict[str, str] = {
    # Research
    "search_flights":        "tools.travel_research",
    "flight_search":         "tools.travel_research",
    "search_hotels":         "tools.travel_research",
    "hotel_search":          "tools.travel_research",
    "hotels_search":         "tools.travel_research",
    "search_trains":         "tools.travel_research",
    "train_search":          "tools.travel_research",
    "get_weather":           "tools.weather",
    "optimize_route":        "tools.route_optimizer",
    "generate_alternatives": "tools.alternative_generator",
    # Constraints & memory
    "check_constraints":     "tools.constraint_checker",
    "load_preferences":      "tools.memory",
    # Booking & payment
    "book_flight":           "tools.booking",
    "flight_booking":        "tools.booking",
    "book_hotel":            "tools.booking",
    "hotel_booking":         "tools.booking",
    "book_train":            "tools.booking",
    "train_booking":         "tools.booking",
    "make_reservation":      "tools.reservation",
    "process_payment":       "tools.payment",
    "payment":               "tools.payment",
    "cancel_booking":        "tools.booking",
    # Notifications
    "send_email_confirmation": "tools.notifications",
    "send_sms_confirmation":   "tools.notifications",
}
