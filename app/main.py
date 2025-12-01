from fastapi import FastAPI, HTTPException, Depends, Request
from pydantic import BaseModel
from .agent_runner import run_agent
from .config import settings
import uvicorn
import asyncio
from typing import Optional

app = FastAPI(title="HyperHire Assistant - LangChain + Groq (MVP)")

class ChatReq(BaseModel):
    query: str
    user: Optional[dict] = None

@app.post("/api/chat")
async def chat(req: ChatReq):
    if not req.query:
        raise HTTPException(status_code=400, detail="query required")
    # Run agent (tool-driven). This will call DB tools and generation tools as needed.
    try:
        resp = await run_agent(req.query)
        return {"ok": True, "response": resp}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {"ok": True}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host=settings.APP_HOST, port=settings.APP_PORT, reload=True)
