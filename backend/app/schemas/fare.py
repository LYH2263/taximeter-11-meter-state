from pydantic import BaseModel, Field

class FareRequest(BaseModel):
    distance_km: float = Field(ge=0)
    slow_min: float = Field(ge=0)
    night: bool = False
    trip_id: int | None = None
    persist: bool = True

class CompareRequest(BaseModel):
    distance_km: float = Field(ge=0)
    slow_min: float = Field(ge=0)
    persist: bool = False

class MeterStartRequest(BaseModel):
    night: bool = False

class MeterReadingRequest(BaseModel):
    distance_km: float = Field(ge=0)
    slow_min: float = Field(ge=0)
