"""Small support-copilot reference integration protected by Renzai Analyze."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, ConfigDict, Field
from renzai_sdk import Action, Renzai


class AnalysisLike(Protocol):
    @property
    def action(self) -> Action: ...

    @property
    def redacted_content(self) -> str | None: ...

    @property
    def request_id(self) -> str | None: ...

    @property
    def risk_score(self) -> int: ...


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str = Field(min_length=1, max_length=8_000)


class ChatResponse(BaseModel):
    decision: str
    request_id: str
    risk_score: int
    provider_called: bool
    response: str | None


@dataclass(slots=True)
class AnalyzeProtector:
    base_url: str
    api_key: str

    def inspect(self, content: str) -> AnalysisLike:
        with Renzai(api_key=self.api_key, base_url=self.base_url) as client:
            return client.analyze(content=content, direction="input")


def mock_provider(_: str) -> str:
    """Return a deterministic synthetic answer without contacting a paid provider."""

    return "Synthetic support response generated after the Renzai decision."


def create_app(protector: AnalyzeProtector | None = None) -> FastAPI:
    resolved = protector or AnalyzeProtector(
        base_url=os.environ.get("RENZAI_BASE_URL", "http://localhost:8080"),
        api_key=os.environ.get("RENZAI_API_KEY", ""),
    )
    app = FastAPI(title="Renzai Protected Support Copilot", docs_url=None, redoc_url=None)

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        return _PAGE

    @app.post("/api/chat", response_model=ChatResponse)
    def chat(body: ChatRequest) -> ChatResponse:
        if not resolved.api_key:
            raise RuntimeError("RENZAI_API_KEY is required in the trusted server environment")
        analysis = resolved.inspect(body.message)
        if analysis.action in {Action.BLOCK, Action.REQUIRE_REVIEW}:
            return ChatResponse(
                decision=analysis.action.value,
                request_id=analysis.request_id or "unknown",
                risk_score=analysis.risk_score,
                provider_called=False,
                response=None,
            )
        if analysis.action is Action.REDACT and analysis.redacted_content is None:
            raise HTTPException(status_code=502, detail="Security inspection failed")
        provider_input = (
            analysis.redacted_content
            if analysis.action is Action.REDACT and analysis.redacted_content is not None
            else body.message
        )
        return ChatResponse(
            decision=analysis.action.value,
            request_id=analysis.request_id or "unknown",
            risk_score=analysis.risk_score,
            provider_called=True,
            response=mock_provider(provider_input),
        )

    return app


app = create_app()

_PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Renzai protected support copilot</title><style>
body{font:16px system-ui;background:#07111f;color:#eaf2ff;max-width:760px;
margin:4rem auto;padding:1rem}
main{background:#101f31;border:1px solid #29445e;border-radius:16px;padding:2rem}
textarea{width:100%;box-sizing:border-box;background:#081725;color:#fff;
border:1px solid #38546d;border-radius:8px;padding:1rem}
button{margin-top:1rem;background:#52d9b8;border:0;border-radius:8px;
padding:.8rem 1.2rem;font-weight:700}
pre{white-space:pre-wrap;background:#081725;padding:1rem;border-radius:8px}
.meta{color:#9dc8f8}</style></head>
<body><main><p class="meta">REFERENCE APPLICATION · SYNTHETIC PROVIDER</p>
<h1>Protected support copilot</h1><p>Every submitted message is inspected by Renzai before the
deterministic local provider path can run.</p><form id="chat"><textarea name="message" rows="6"
placeholder="Ask a safe support question"></textarea><button>Send securely</button></form>
<pre id="result" aria-live="polite">Ready.</pre></main><script>
document.querySelector('#chat').addEventListener('submit',async(e)=>{e.preventDefault();
const message=new FormData(e.target).get('message');const result=document.querySelector('#result');
result.textContent='Inspecting…';const response=await fetch('/api/chat',{method:'POST',headers:{
'Content-Type':'application/json'},body:JSON.stringify({message})});result.textContent=JSON.stringify(
await response.json(),null,2);});</script></body></html>"""
