from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .db import init_db
from .routers import jobs, money, webhooks
from .seed import seed
from .services.claude import ClaudeUnavailable


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    seed()
    yield


app = FastAPI(title="Open Tradesman API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in get_settings().app_origin.split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ClaudeUnavailable)
async def claude_unavailable(_: Request, exc: ClaudeUnavailable):
    return JSONResponse(status_code=502, content={"detail": f"The AI couldn't finish this one: {exc}. Try again."})


app.include_router(jobs.router)
app.include_router(money.router)
app.include_router(webhooks.router)


@app.get("/health")
def health():
    return {"ok": True}
