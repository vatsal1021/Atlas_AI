"""Deterministic Booking Requirements Validator.

Validates that all required fields for a booking type (train, flight, hotel) are
present and valid in the state. LLM is NOT the authority on completeness.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from services.booking_requirements.registry import get_requirements_for_type


def validate_booking_requirements(
    booking_type: str,
    booking_details: Optional[Dict[str, Any]] = None,
    passenger_info: Optional[List[Dict[str, Any]]] = None,
    guest_info: Optional[Dict[str, Any]] = None,
    extracted_entities: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Deterministically check if all required booking fields are present.

    Returns structured validation result dict:
    {
      "ready": bool,
      "booking_type": str,
      "missing_fields": list[str],
      "validated_fields": list[str],
      "collected_info": dict,
    }
    """
    norm_type = (booking_type or "").lower().strip()
    required_fields = get_requirements_for_type(norm_type)
    
    details = booking_details or {}
    passengers = passenger_info or details.get("passengers", [])
    guest = guest_info or details.get("guest_info", {})
    entities = extracted_entities or {}

    missing_fields: List[str] = []
    validated_fields: List[str] = []
    collected_info: Dict[str, Any] = {}

    if norm_type == "train":
        pax_list = passengers if (isinstance(passengers, list) and passengers) else []
        p0 = pax_list[0] if pax_list else {}

        name = p0.get("name") or details.get("passenger_name") or details.get("name") or entities.get("passenger_name")
        age = p0.get("age") or details.get("passenger_age") or details.get("age") or entities.get("passenger_age")
        gender = p0.get("gender") or details.get("passenger_gender") or details.get("gender") or entities.get("passenger_gender")
        berth = p0.get("berth_preference") or p0.get("berth") or details.get("berth_preference") or details.get("berth") or entities.get("berth_preference")
        travel_class = p0.get("class") or p0.get("travel_class") or details.get("travel_class") or details.get("class") or entities.get("travel_class")

        field_map = {
            "passenger.name": name,
            "passenger.age": age,
            "passenger.gender": gender,
            "passenger.berth_preference": berth,
            "passenger.class": travel_class,
        }

        for req_field in required_fields:
            val = field_map.get(req_field)
            if val is not None and str(val).strip() != "":
                validated_fields.append(req_field)
                collected_info[req_field] = val
            else:
                missing_fields.append(req_field)

    elif norm_type == "flight":
        p0 = passengers[0] if (isinstance(passengers, list) and passengers) else {}

        name = p0.get("name") or details.get("passenger_name") or details.get("name") or entities.get("passenger_name")
        dob_age = p0.get("dob_or_age") or p0.get("age") or p0.get("dob") or details.get("dob_or_age") or details.get("age") or entities.get("passenger_age")
        gender = p0.get("gender") or details.get("passenger_gender") or details.get("gender") or entities.get("passenger_gender")
        passport_id = p0.get("passport_or_id") or p0.get("id_number") or details.get("passport_or_id") or details.get("id_number") or entities.get("passport_or_id")
        seat = p0.get("seat_preference") or details.get("seat_preference") or details.get("seat") or entities.get("seat_preference")

        field_map = {
            "passenger.name": name,
            "passenger.dob_or_age": dob_age,
            "passenger.gender": gender,
            "passenger.passport_or_id": passport_id,
            "passenger.seat_preference": seat,
        }

        for req_field in required_fields:
            val = field_map.get(req_field)
            if val is not None and str(val).strip() != "":
                validated_fields.append(req_field)
                collected_info[req_field] = val
            else:
                missing_fields.append(req_field)

    elif norm_type == "hotel":
        name = guest.get("name") or details.get("guest_name") or details.get("name") or entities.get("guest_name")
        contact = guest.get("contact_email_or_phone") or guest.get("email") or guest.get("phone") or details.get("contact") or entities.get("contact")
        checkin = guest.get("checkin_date") or details.get("checkin_date") or details.get("checkin") or entities.get("start_date")
        checkout = guest.get("checkout_date") or details.get("checkout_date") or details.get("checkout") or entities.get("end_date")
        room_type = guest.get("room_type") or details.get("room_type") or entities.get("room_type") or "Standard Room"

        field_map = {
            "guest.name": name,
            "guest.contact_email_or_phone": contact,
            "guest.checkin_date": checkin,
            "guest.checkout_date": checkout,
            "guest.room_type": room_type,
        }

        for req_field in required_fields:
            val = field_map.get(req_field)
            if val is not None and str(val).strip() != "":
                validated_fields.append(req_field)
                collected_info[req_field] = val
            else:
                missing_fields.append(req_field)

    else:
        # Unknown booking type or generic
        missing_fields = []
        validated_fields = []

    is_ready = len(missing_fields) == 0 and len(required_fields) > 0

    return {
        "ready": is_ready,
        "booking_type": norm_type,
        "missing_fields": missing_fields,
        "validated_fields": validated_fields,
        "collected_info": collected_info,
    }
