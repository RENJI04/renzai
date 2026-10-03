"""Call the limited Renzai Gateway from trusted server-side Python."""

import os

from renzai_sdk import ChatMessage, Renzai

with Renzai(
    api_key=os.environ["RENZAI_API_KEY"],
    base_url=os.environ.get("RENZAI_BASE_URL", "http://localhost:8000"),
) as client:
    result = client.gateway.create(
        model="configured-model",
        messages=[ChatMessage(role="user", content="Safe synthetic example")],
    )

print(result.content)
