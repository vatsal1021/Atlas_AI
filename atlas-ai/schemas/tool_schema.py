"""Pydantic schemas for tool inputs and outputs."""

from __future__ import annotations

from pydantic import BaseModel, Field


class FlightOption(BaseModel):
    """A single flight search result."""

    airline: str = Field(description="Airline name")
    flight_number: str = Field(description="Flight number")
    origin: str = Field(description="Origin airport/city")
    destination: str = Field(description="Destination airport/city")
    departure_time: str = Field(description="ISO datetime of departure")
    arrival_time: str = Field(description="ISO datetime of arrival")
    duration_hours: float = Field(description="Flight duration in hours")
    price: float = Field(description="Ticket price")
    currency: str = Field(default="INR")
    stops: int = Field(default=0, description="Number of stops")
    cabin_class: str = Field(default="economy")


class HotelOption(BaseModel):
    """A single hotel search result."""

    name: str = Field(description="Hotel name")
    location: str = Field(description="Hotel area / address")
    rating: float = Field(ge=0.0, le=5.0, description="Star rating")
    price_per_night: float = Field(description="Price per night")
    currency: str = Field(default="INR")
    amenities: list[str] = Field(default_factory=list)
    review_score: float = Field(default=0.0, ge=0.0, le=10.0, description="Guest review score")
    available: bool = Field(default=True)


class DailyWeather(BaseModel):
    """Weather forecast for a single day."""

    date: str = Field(description="ISO date")
    temperature_high: float = Field(description="High temp in Celsius")
    temperature_low: float = Field(description="Low temp in Celsius")
    condition: str = Field(description="e.g. Sunny, Rainy, Cloudy")
    rain_probability: float = Field(ge=0.0, le=1.0, description="Rain probability 0-1")
    humidity: float = Field(ge=0.0, le=100.0, description="Humidity percentage")
    wind_speed_kmh: float = Field(default=0.0, description="Wind speed in km/h")


class ConstraintViolation(BaseModel):
    """A detected constraint violation."""

    constraint: str = Field(description="The constraint that was violated")
    violation: str = Field(description="Description of the violation")
    severity: str = Field(default="warning", description="warning | error")
    suggestion: str = Field(default="", description="How to fix it")
