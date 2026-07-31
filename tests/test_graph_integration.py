"""Integration test for the full LangGraph planning loop."""

from __future__ import annotations

from unittest.mock import patch

from graph.graph import compile_graph
from graph.planner_loop import create_initial_state
from tests.conftest import (
    SAMPLE_PARSED_GOAL,
    SAMPLE_SUB_GOALS,
    SAMPLE_PLANNER_ACTIONS,
    SAMPLE_WORLD_FACTS,
)


def test_full_graph_loop_to_completion(mock_llm_response):
    """End-to-end test simulating a successful planning session."""

    # Set up mock responses for each node that calls an LLM
    def side_effect_mock(*args, **kwargs):
        # We can inspect the prompt to figure out which node is calling,
        # or we can just rely on the order of calls if we mock the whole chain.
        # For a robust test, it's easier to patch each node's get_llm individually,
        # but let's do a sequence of mock responses.
        pass

    mock_goal = mock_llm_response(SAMPLE_PARSED_GOAL)
    mock_decomp = mock_llm_response(SAMPLE_SUB_GOALS)
    mock_planner = mock_llm_response(SAMPLE_PLANNER_ACTIONS)
    mock_planner_empty = mock_llm_response([])  # Second iteration: no actions
    mock_world = mock_llm_response(SAMPLE_WORLD_FACTS)
    
    # First eval: not satisfied
    eval_response_1 = {
        "sub_goal_statuses": {"sg-1": {"satisfied": True, "reasoning": "Done."}},
        "all_satisfied": False,
        "summary": "Need more info."
    }
    mock_eval_1 = mock_llm_response(eval_response_1)
    
    # Second eval: satisfied
    eval_response_2 = {
        "sub_goal_statuses": {
            "sg-1": {"satisfied": True, "reasoning": "Done."},
            "sg-2": {"satisfied": True, "reasoning": "Done."},
            "sg-3": {"satisfied": True, "reasoning": "Done."},
            "sg-4": {"satisfied": True, "reasoning": "Done."},
            "sg-5": {"satisfied": True, "reasoning": "Done."},
        },
        "all_satisfied": True,
        "summary": "All done."
    }
    mock_eval_2 = mock_llm_response(eval_response_2)

    # QA Mocks (Phase 2)
    reflection_response = {"gaps": [], "overall_confidence": 0.9}
    mock_reflection = mock_llm_response(reflection_response)
    
    critic_response = {"issues": [], "overall_rating": "excellent", "should_revise": False}
    mock_critic = mock_llm_response(critic_response)
    
    explainability_response = {"explanation": {"decisions": []}}
    mock_explainability = mock_llm_response(explainability_response)

    # Patch the LLMs in each node
    with patch("nodes.goal_understanding.get_llm", return_value=mock_goal), \
         patch("nodes.goal_decomposition.get_llm", return_value=mock_decomp), \
         patch("nodes.objective_planner.get_llm", side_effect=[mock_planner, mock_planner_empty]), \
         patch("nodes.world_model.get_llm", return_value=mock_world), \
         patch("nodes.goal_evaluator.get_llm", side_effect=[mock_eval_1, mock_eval_2]), \
         patch("nodes.reflection.get_llm", return_value=mock_reflection), \
         patch("nodes.critic.get_llm", return_value=mock_critic), \
         patch("nodes.explainability.get_llm", return_value=mock_explainability), \
         patch("graph.router.ENABLE_REFLECTION", True), \
         patch("graph.router.ENABLE_CRITIC", True), \
         patch("graph.router.ENABLE_EXPLAINABILITY", True):
        
        initial_state = create_initial_state(
            user_input="Plan a trip to Japan",
            max_iterations=3,
        )
        
        graph = compile_graph()
        config = {"configurable": {"thread_id": "test_thread_1"}}
        final_state = graph.invoke(initial_state, config=config)

    # Verify final state
    assert final_state["goal_satisfied"] is True
    assert final_state["planner_iteration"] == 2
    assert "evidence" in final_state
    assert "world_facts" in final_state
    assert final_state["planning_complete"] is True
