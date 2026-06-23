from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import BASE_DIR
from .database import Base, engine
from .routers import briefing, events, health, ops_intel
from .seed import seed
from .services.ops_intel_collector import start_periodic_collector, stop_periodic_collector

app = FastAPI(title="Ops Briefing")
Base.metadata.create_all(bind=engine)
seed()

app.include_router(briefing.router)
app.include_router(events.router)
app.include_router(health.router)
app.include_router(ops_intel.router)
app.mount("/static", StaticFiles(directory=BASE_DIR / "src" / "static"), name="static")


@app.on_event("startup")
async def startup():
    start_periodic_collector()


@app.on_event("shutdown")
async def shutdown():
    stop_periodic_collector()


@app.get("/")
def index():
    return FileResponse(BASE_DIR / "src" / "static" / "index.html")
