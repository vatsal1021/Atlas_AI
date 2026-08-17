"""Test suite for Sequential Item-by-Item Booking Queue & Multi-Passenger List Extraction.
"""

from __future__ import annotations

import logging
import os
import sys

# Ensure root directory is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from nodes.booking_requirements import booking_requirements_node
from services.booking_requirements.validator import validate_booking_requirements
from graph.graph import compile_graph

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_multi_passenger_extraction_and_validation():
    print("\n--- Test 1: Multi-Passenger Extraction & Validation ---")
    extracted_entities = {
        "destination": "Mumbai",
        "origin": "Kanpur",
        "start_date": "2026-09-10",
        "passengers": [
            {"name": "Ansh Adarsh", "age": 21, "gender": "Male", "berth_preference": "Lower", "class": "3A"},
            {"name": "Passenger Two", "age": 19, "gender": "Female", "berth_preference": "Lower", "class": "3A"},
        ]
    }
    state = {
        "user_input": "here are passenger details",
        "extracted_entities": extracted_entities,
        "passenger_info": [],
        "pending_tool_call": {"tool": "book_train", "arguments": {}},
    }

    result = booking_requirements_node(state)
    passenger_info = result["passenger_info"]
    print(f"Extracted passenger_info count: {len(passenger_info)}")
    print(f"Passengers: {passenger_info}")

    assert len(passenger_info) == 2, f"Expected 2 passengers, got {len(passenger_info)}"
    assert passenger_info[0]["name"] == "Ansh Adarsh", "Passenger 1 name mismatch"
    assert passenger_info[1]["name"] == "Passenger Two", "Passenger 2 name mismatch"
    assert passenger_info[1]["age"] == 19, "Passenger 2 age mismatch"
    print("  PASS  Multi-passenger list correctly preserved in passenger_info")

    val_res = validate_booking_requirements(
        booking_type="train",
        booking_details={},
        passenger_info=passenger_info,
        guest_info={},
        extracted_entities=extracted_entities,
    )
    print(f"Validation Result: ready={val_res['ready']}, missing={val_res['missing_fields']}")
    assert val_res["ready"] is True, f"Expected ready=True, got missing={val_res['missing_fields']}"
    print("  PASS  Multi-passenger list passes validation successfully")


def test_sequential_booking_queue_initialization():
    print("\n--- Test 2: Sequential Booking Queue Initialization ---")
    state = {
        "user_input": "book this Grand Hyatt Mumbai and gareeb rath express train",
        "extracted_entities": {"destination": "Mumbai", "origin": "Kanpur", "start_date": "2026-09-10"},
        "pending_tool_call": {},
        "passenger_info": [],
        "guest_info": {},
    }

    result = booking_requirements_node(state)
    queue = result.get("booking_queue", [])
    index = result.get("current_booking_index", 0)
    booking_type = result.get("booking_type", "")

    print(f"Booking Queue: {queue}")
    print(f"Current Index: {index}")
    print(f"Active Booking Type: {booking_type}")

    assert len(queue) == 2, f"Expected 2 queue items (train and hotel), got {len(queue)}"
    assert queue[0]["type"] == "train", f"Expected item 1 to be train, got {queue[0]['type']}"
    assert queue[1]["type"] == "hotel", f"Expected item 2 to be hotel, got {queue[1]['type']}"
    assert booking_type == "train", f"Expected active item to be train first, got {booking_type}"
    print("  PASS  Sequential booking queue correctly initialized with train item first")


def run_all_tests():
    print("=== RUNNING SEQUENTIAL BOOKING & MULTI-PASSENGER TEST SUITE ===")
    test_multi_passenger_extraction_and_validation()
    test_sequential_booking_queue_initialization()
    print("\n============================================================")
    print("ALL SEQUENTIAL BOOKING & MULTI-PASSENGER TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    run_all_tests()
