"""
backend/main.py
===============
CascadeGuard AI — FastAPI Entry Point (Phase 15)

Starts the FastAPI application on port 5000.
Flask backend (backend/app.py) continues running on port 5050 as a fallback.

Run with:
    python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 5000

API documentation:
    http://127.0.0.1:5000/docs   (Swagger UI)
    http://127.0.0.1:5000/redoc  (ReDoc)
"""
import sys
import os
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# ── Path: ensure 'backend/' is on sys.path so business modules resolve ────────
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

PROJECT_ROOT = os.path.dirname(BACKEND_DIR)

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

import state

# ── Route modules ─────────────────────────────────────────────────────────────
from api.routes_health      import router as health_router
from api.routes_live        import router as live_router
from api.routes_scenarios   import router as scenarios_router
from api.routes_realtime    import router as realtime_router
from api.routes_telemetry   import router as telemetry_router
from api.routes_site_config import router as site_config_router
from api.routes_climate     import router as climate_router
from api.routes_incidents   import router as incidents_router
from api.routes_sites       import router as sites_router
from api.routes_regional    import router as regional_router
from api.routes_reports     import router as reports_router
from api.routes_prediction  import router as prediction_router
from api.routes_decision    import router as decision_router
from api.routes_incidents_phase19 import router as incidents_p19_router
from api.routes_learning_phase20 import router as learning_p20_router
from api.routes_scenarios_phase21 import router as scenarios_p21_router
from api.routes_optimization_phase22 import router as optimization_p22_router
from api.routes_cascadeguard import router as cascadeguard_router

# ── Lifespan: load all models once at startup ─────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    state.load_all_models()
    yield
    # Shutdown: nothing to clean up


# ── App definition ────────────────────────────────────────────────────────────
app = FastAPI(
    title="CascadeGuard AI Command Center",
    description=(
        "Real-time multi-asset climate resilience intelligence platform. "
        "Monitors Power Transformers, HVAC Chillers, and Industrial Water Pumps "
        "across facilities using live Open-Meteo weather data, "
        "ML cascade risk models, SHAP explainability, and incident alerting."
    ),
    version="16.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)


# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition", "Content-Type"],
)


# ── Request latency logging middleware ────────────────────────────────────────
class LatencyLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        t0 = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
        print(f"  [{request.method}] {request.url.path} → {response.status_code} ({elapsed_ms}ms)")
        return response

app.add_middleware(LatencyLoggingMiddleware)


from fastapi.exceptions import HTTPException as FastAPIHTTPException, RequestValidationError

# ── Global exception handlers ────────────────────────────────────────────────
@app.exception_handler(FastAPIHTTPException)
async def http_exception_handler(request: Request, exc: FastAPIHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "error": str(exc.detail)}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=400,
        content={"success": False, "error": f"Validation Error: {str(exc)}"}
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import traceback
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": str(exc)}
    )


# ── Include API routers ───────────────────────────────────────────────────────
app.include_router(cascadeguard_router,   prefix="/api", tags=["CascadeGuard Core Intelligence"])

app.include_router(health_router,      prefix="/api", tags=["Health"])
app.include_router(live_router,        prefix="/api", tags=["Fleet & Live Analysis"])
app.include_router(scenarios_p21_router, prefix="/api", tags=["Phase 21 Digital Twin & What-If Climate Simulator"])
app.include_router(scenarios_router,   prefix="/api", tags=["Scenarios"])
app.include_router(realtime_router,    prefix="/api", tags=["Real-Time Analysis"])
app.include_router(telemetry_router,   prefix="/api", tags=["OT Telemetry"])
app.include_router(site_config_router, prefix="/api", tags=["Site Configuration"])
app.include_router(climate_router,     prefix="/api", tags=["Climate Intelligence"])
app.include_router(incidents_p19_router, prefix="/api", tags=["Phase 19 Incident Management & Resilience Orchestration"])
app.include_router(incidents_router,   prefix="/api", tags=["Incident Intelligence"])
app.include_router(reports_router,     prefix="/api", tags=["PDF Reports"])
app.include_router(sites_router,       prefix="/api", tags=["Regional Sites"])
app.include_router(regional_router,    prefix="/api", tags=["Regional Command"])
app.include_router(prediction_router,  prefix="/api", tags=["Predictive Climate Risk & Failure Forecasting"])
app.include_router(decision_router,    prefix="/api", tags=["AI Climate Resilience Decision Engine"])
app.include_router(learning_p20_router, prefix="/api", tags=["Phase 20 Continuous Learning & Adaptive AI"])
app.include_router(optimization_p22_router, prefix="/api", tags=["Phase 22 Resilience Optimization & Prescriptive Action Planner"])



# ── Static frontend serving ───────────────────────────────────────────────────
FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend")

if os.path.isdir(FRONTEND_DIR):
    # Mount static assets (CSS, JS, images) — NOT at root so /docs still works
    app.mount("/static-assets", StaticFiles(directory=FRONTEND_DIR), name="static-assets")


@app.get("/", include_in_schema=False)
async def index_page():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse({"success": True, "message": "CascadeGuard AI FastAPI Server"})


@app.get("/{path:path}", include_in_schema=False)
async def serve_static(path: str):
    # Don't catch API routes (fallthrough)
    if path.startswith("api/"):
        return JSONResponse({"success": False, "error": "Endpoint not found"}, status_code=404)
    file_path = os.path.join(FRONTEND_DIR, path)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path)
    return JSONResponse({"success": False, "error": "File not found"}, status_code=404)


# ── Direct run ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 5000))
    print("=" * 60)
    print("CASCADEGUARD AI — FastAPI Command Center")
    print(f"Server        : http://127.0.0.1:{port}")
    print(f"API Docs      : http://127.0.0.1:{port}/docs")
    print(f"ReDoc         : http://127.0.0.1:{port}/redoc")
    print("=" * 60)
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
        reload=False
    )
