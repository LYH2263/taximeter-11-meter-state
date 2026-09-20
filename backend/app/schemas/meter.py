from pydantic import BaseModel, Field

class MeterStartRequest(BaseModel):
    night: bool = False

class MeterReadingRequest(BaseModel):
    distance_km: float = Field(ge=0)
    slow_min: float = Field(ge=0)
