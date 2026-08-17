"""Integration test for new runtime observability and tool architecture."""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, ".")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from app.settings import TOOL_REGISTRY
from app.tracing import ExecutionTracker, start_execution_tracker
from tools.notifications import send_email_confirmation, send_sms_confirmation

PASS = 0
FAIL = 0

def check(label, condition, got=""):
    global PASS, FAIL
    if condition:
        print(f"  PASS  {label}")
        PASS += 1
    else:
        print(f"  FAIL  {label}  | got: {got}")
        FAIL += 1

base_runtime_dir = Path("runtime")
traces_dir = base_runtime_dir / "traces"

# 1. Test Notification Tools Execution & Auto-creation of JSON files
tracker = start_execution_tracker(run_id="archtest_001", user_input="Test notification tools")

# Invoke send_email_confirmation tool
tracker.track_tool_start("send_email_confirmation", {"recipient": "traveler@example.com", "subject": "Flight Confirmation", "booking_id": "FLT-999"})
email_result = send_email_confirmation(recipient="traveler@example.com", subject="Flight Confirmation", booking_id="FLT-999")
tracker.track_tool_call("send_email_confirmation", {"recipient": "traveler@example.com", "subject": "Flight Confirmation", "booking_id": "FLT-999"}, email_result, status="completed")

# Invoke send_sms_confirmation tool
tracker.track_tool_start("send_sms_confirmation", {"recipient": "+919876543210", "booking_id": "FLT-999"})
sms_result = send_sms_confirmation(recipient="+919876543210", booking_id="FLT-999")
tracker.track_tool_call("send_sms_confirmation", {"recipient": "+919876543210", "booking_id": "FLT-999"}, sms_result, status="completed")

tracker.track_workflow_complete(success=True)

# 2. Check JSON filenames directly match tool names
email_json_path = base_runtime_dir / "send_email_confirmation.json"
sms_json_path = base_runtime_dir / "send_sms_confirmation.json"

check("send_email_confirmation.json created automatically", email_json_path.exists(), email_json_path)
check("send_sms_confirmation.json created automatically", sms_json_path.exists(), sms_json_path)

if email_json_path.exists():
    email_data = json.loads(email_json_path.read_text(encoding="utf-8"))
    check("Email JSON tool_name is send_email_confirmation", email_data.get("tool_name") == "send_email_confirmation", email_data.get("tool_name"))
    check("Email JSON status is completed", email_data.get("status") == "completed", email_data.get("status"))
    check("Email JSON has execution_count >= 1", email_data.get("execution_count", 0) >= 1, email_data.get("execution_count"))

if sms_json_path.exists():
    sms_data = json.loads(sms_json_path.read_text(encoding="utf-8"))
    check("SMS JSON tool_name is send_sms_confirmation", sms_data.get("tool_name") == "send_sms_confirmation", sms_data.get("tool_name"))
    check("SMS JSON status is completed", sms_data.get("status") == "completed", sms_data.get("status"))

# 3. Check persistent update on multiple tool calls
tracker.track_tool_start("send_email_confirmation", {"recipient": "traveler@example.com", "subject": "Update", "booking_id": "FLT-999"})
email_result_2 = send_email_confirmation(recipient="traveler@example.com", subject="Update", booking_id="FLT-999")
tracker.track_tool_call("send_email_confirmation", {"recipient": "traveler@example.com", "subject": "Update", "booking_id": "FLT-999"}, email_result_2, status="completed")

if email_json_path.exists():
    email_data_updated = json.loads(email_json_path.read_text(encoding="utf-8"))
    check("Persistent update: execution_count incremented", email_data_updated.get("execution_count", 0) >= 2, email_data_updated.get("execution_count"))

# 4. Check trace files location
trace_file = traces_dir / f"trace_{tracker.run_id}.log"
check("Trace log exists strictly in runtime/traces/", trace_file.exists(), trace_file)

# 5. Check no log files directly in runtime/
logs_in_root_runtime = list(base_runtime_dir.glob("*.log"))
check("No .log files exist directly in runtime/", len(logs_in_root_runtime) == 0, logs_in_root_runtime)

# 7. Check alias normalization and single-result structure
tracker.track_tool_start("hotel_search", {"destination": "Jaipur"})
tracker.track_tool_call("hotel_search", {"destination": "Jaipur"}, [{"name": "Taj Jaipur", "price": 5000}], status="completed")

hotel_json_path = base_runtime_dir / "search_hotels.json"
hotel_alias_path = base_runtime_dir / "hotel_search.json"

check("Alias 'hotel_search' normalizes to 'search_hotels.json'", hotel_json_path.exists(), hotel_json_path)
check("Duplicate file 'hotel_search.json' is NOT created", not hotel_alias_path.exists(), hotel_alias_path)

if hotel_json_path.exists():
    h_data = json.loads(hotel_json_path.read_text(encoding="utf-8"))
    check("Hotel JSON tool_name is canonical 'search_hotels'", h_data.get("tool_name") == "search_hotels", h_data.get("tool_name"))
    check("Hotel JSON result is present at top-level", "result" in h_data, list(h_data.keys()))
    check("Hotel JSON result is NOT duplicated inside current_call", "result" not in h_data.get("current_call", {}), list(h_data.get("current_call", {}).keys()))

print(f"\n{'='*60}")
print(f"Results: {PASS} passed, {FAIL} failed")
if FAIL == 0:
    print("RUNTIME ARCHITECTURE TEST PASSED SUCCESSFULLY!")
