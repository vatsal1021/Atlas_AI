"""Named edge / node constants for the new AtlasAI LangGraph state graph."""

# ── Relevance & intent ────────────────────────────────────────────────
INTENT_NODE            = "intent_node"
IRRELEVANT_RESPONSE    = "irrelevant_response"

# ── Entity & negotiation ──────────────────────────────────────────────
ENTITY_EXTRACT         = "entity_extract"
NEGOTIATION_CLASSIFY   = "negotiation_classification"
NEGOTIATION_QUESTION   = "negotiation_question"

# ── Planning ──────────────────────────────────────────────────────────
PLAN_PROPOSAL          = "plan_proposal"

# ── ReAct loop ────────────────────────────────────────────────────────
REACT                  = "react"
TOOL_EXECUTION         = "tool_execution"

# ── Human approval ────────────────────────────────────────────────────
HUMAN_APPROVAL         = "human_approval"

# ── Quality assurance ─────────────────────────────────────────────────
REFLECT                = "reflect"
CRITIC_GATE            = "critic_gate"
CRITIC                 = "critic"

# ── Final response ────────────────────────────────────────────────────
RELEVANT_RESPONSE      = "relevant_response"
