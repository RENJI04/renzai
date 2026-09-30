"""Outbound ports for optional identity-message delivery adapters."""

from typing import Protocol


class IdentityTokenDelivery(Protocol):
    async def send_password_reset(self, email: str, token: str) -> None: ...

    async def send_email_verification(self, email: str, token: str) -> None: ...
