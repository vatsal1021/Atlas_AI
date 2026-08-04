"""Named edge constants for the LangGraph state graph."""

# ---------------------------------------------------------------------------
# Phase 1 — core planning loop
# ---------------------------------------------------------------------------
GOAL_UNDERSTANDING = "goal_understanding"
GOAL_DECOMPOSITION = "goal_decomposition"
OBJECTIVE_PLANNER = "objective_planner"
CAPABILITY_DISPATCHER = "capability_dispatcher"
EVIDENCE_AGGREGATOR = "evidence_aggregator"
WORLD_MODEL = "world_model"
GOAL_EVALUATOR = "goal_evaluator"

# ---------------------------------------------------------------------------
# Phase 2 — quality-assurance layer
# ---------------------------------------------------------------------------
REFLECTION = "reflection"
CRITIC = "critic"
EXPLAINABILITY = "explainability"

# ---------------------------------------------------------------------------
# Phase 3 — human approval, execution, recovery, memory
# ---------------------------------------------------------------------------
META_REASONER = "meta_reasoner"
HUMAN_APPROVAL = "human_approval"
ACTION_DISPATCHER = "action_dispatcher"
MEMORY_UPDATE = "memory_update"
