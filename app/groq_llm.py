from langchain.llms.base import LLM
from typing import Optional, List, Mapping, Any
from pydantic import BaseModel
from .config import settings
import httpx
import json

# Implement a simple LangChain LLM wrapper for Groq-style HTTP API.
class GroqLLM(LLM, BaseModel):
    api_key: str = settings.GROQ_API_KEY
    model: str = settings.GROQ_MODEL
    temperature: float = 0.0
    max_tokens: int = 512

    class Config:
        arbitrary_types_allowed = True

    def _call(self, prompt: str, stop: Optional[List[str]] = None) -> str:
        # Synchronous call wrapper used by LangChain. We use httpx sync client.
        # Replace "https://api.groq.ai/v1/generate" with the real provider endpoint & adapt parsing.
        url = "https://api.groq.ai/v1/generate"  # <<--- replace this
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "prompt": prompt,
            "temperature": float(self.temperature),
            "max_tokens": int(self.max_tokens)
        }
        with httpx.Client(timeout=30.0) as client:
            r = client.post(url, json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()
        # Example parsing — adapt to real response shape
        # try common keys:
        out = data.get("text") or data.get("generated_text") or data.get("output") or ""
        if not out:
            # fallback: dump json
            out = json.dumps(data)
        return out

    async def _acall(self, prompt: str, stop: Optional[List[str]] = None) -> str:
        # LangChain may call _acall for async usage. We'll do an httpx.AsyncClient.
        url = "https://api.groq.ai/v1/generate"  # <<--- replace this
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "prompt": prompt,
            "temperature": float(self.temperature),
            "max_tokens": int(self.max_tokens)
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(url, json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()
        out = data.get("text") or data.get("generated_text") or data.get("output") or ""
        if not out:
            out = json.dumps(data)
        return out

    @property
    def _identifying_params(self) -> Mapping[str, Any]:
        return {"model": self.model}

    @property
    def _llm_type(self) -> str:
        return "groq"
