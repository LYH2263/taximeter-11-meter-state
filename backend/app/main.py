from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app import seed
from app.routers import api
from app.services.taxi_service import MeterStateError

app = FastAPI(title="Taximeter", version="0.2.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
def _startup(): seed.init_db()

@app.exception_handler(MeterStateError)
def _meter_state_error(request, exc):
    return JSONResponse(status_code=409, content={"detail": str(exc)})

app.include_router(api)

@app.get("/api/health")
def health(): return {"ok": True, "project": "taximeter"}
