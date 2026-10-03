from __future__ import annotations

import asyncio

import httpx
import pytest

from conftest import analyze_payload
from renzai_sdk import AsyncRenzai, Direction


@pytest.mark.asyncio
async def test_async_analyze_and_context_cleanup() -> None:
    seen = False

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal seen
        seen = True
        return httpx.Response(
            200,
            json=analyze_payload(),
            headers={"X-Request-ID": "async-request"},
            request=request,
        )

    async with AsyncRenzai(
        api_key="rz_dev_example_not_real",
        base_url="https://renzai.example",
        transport=httpx.MockTransport(handler),
    ) as client:
        result = await client.analyze(content="synthetic", direction=Direction.INPUT)
    assert seen is True
    assert result.request_id == "async-request"


@pytest.mark.asyncio
async def test_async_cancellation_is_not_normalized() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        raise asyncio.CancelledError

    async with AsyncRenzai(
        api_key="rz_dev_example_not_real",
        base_url="https://renzai.example",
        transport=httpx.MockTransport(handler),
    ) as client:
        with pytest.raises(asyncio.CancelledError):
            await client.analyze(content="synthetic", direction=Direction.INPUT)
