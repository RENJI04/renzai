"""A scoped FastAPI helper; it does not inspect arbitrary inbound request bodies."""

import os

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from renzai_sdk import Action, AsyncRenzai

router = APIRouter()


class SelectedText(BaseModel):
    text: str


@router.post("/draft")
async def draft(payload: SelectedText) -> dict[str, str]:
    async with AsyncRenzai(
        api_key=os.environ["RENZAI_API_KEY"],
        base_url=os.environ.get("RENZAI_BASE_URL", "http://localhost:8000"),
    ) as client:
        analysis = await client.analyze(content=payload.text, direction="input")
    if analysis.action in {Action.BLOCK, Action.REQUIRE_REVIEW}:
        raise HTTPException(status_code=403, detail="Request withheld by Renzai policy")
    return {"status": "eligible_for_application_model_flow"}
