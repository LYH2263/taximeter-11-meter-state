from fastapi import APIRouter
from app.schemas.meter import MeterReadingRequest, MeterStartRequest
from app.services.taxi_service import TaxiService

router = APIRouter()

@router.get("/meter")
def get_meter():
    with TaxiService() as s: return s.meter_status()

@router.post("/meter/start")
def start_meter(body: MeterStartRequest):
    with TaxiService() as s: return s.meter_start(body.night)

@router.post("/meter/reading")
def update_reading(body: MeterReadingRequest):
    with TaxiService() as s: return s.meter_update_reading(body.distance_km, body.slow_min)

@router.post("/meter/stop")
def stop_meter():
    with TaxiService() as s: return s.meter_stop()

@router.post("/meter/settle")
def settle_meter():
    with TaxiService() as s: return s.meter_settle()
