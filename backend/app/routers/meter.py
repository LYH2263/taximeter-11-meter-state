from fastapi import APIRouter, HTTPException

from app.schemas.fare import MeterReadingRequest, MeterStartRequest
from app.services.taxi_service import MeterError, TaxiService

router = APIRouter()


def _run(action, *args):
    try:
        with TaxiService() as s:
            return action(s, *args)
    except MeterError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/meter")
def get_meter():
    with TaxiService() as s:
        return s.meter_state()


@router.post("/meter/start")
def start_meter(body: MeterStartRequest):
    return _run(TaxiService.meter_start, body.night)


@router.post("/meter/readings")
def update_readings(body: MeterReadingRequest):
    return _run(lambda s: s.meter_update(body.distance_km, body.slow_min))


@router.post("/meter/stop")
def stop_meter():
    return _run(TaxiService.meter_stop)


@router.post("/meter/checkout")
def checkout_meter():
    return _run(TaxiService.meter_checkout)
