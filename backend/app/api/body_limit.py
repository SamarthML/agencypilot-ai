"""Reject oversized request bodies before they are buffered.

The upload routes check file sizes, but by then Starlette's multipart parser has already spooled
the whole body to memory/disk. This ASGI middleware enforces a request-wide cap first: an
oversized Content-Length is refused before any body is read, and bodies without one (chunked)
are counted as they stream and cut off at the limit.
"""

import json

from starlette.types import ASGIApp, Message, Receive, Scope, Send

MB = 1024 * 1024


class BodyTooLargeError(Exception):
    """Raised from `receive` once a streamed body passes the limit."""


class BodySizeLimitMiddleware:
    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        if self._declared_length(scope) > self.max_bytes:
            await self._reject(send)
            return
        await self._guarded(scope, receive, send)

    async def _guarded(self, scope: Scope, receive: Receive, send: Send) -> None:
        received = 0
        exceeded = False

        async def limited_receive() -> Message:
            nonlocal received, exceeded
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    exceeded = True
                    raise BodyTooLargeError
            return message

        async def guarded_send(message: Message) -> None:
            # FastAPI turns body-read errors into its own 400; once over the limit, a 413 wins.
            if not exceeded:
                await send(message)

        try:
            await self.app(scope, limited_receive, guarded_send)
        except BodyTooLargeError:
            pass
        if exceeded:
            await self._reject(send)

    @staticmethod
    def _declared_length(scope: Scope) -> int:
        for name, value in scope.get("headers", []):
            if name == b"content-length":
                try:
                    return int(value)
                except ValueError:
                    return 0
        return 0

    async def _reject(self, send: Send) -> None:
        detail = f"Request body is larger than {self.max_bytes / MB:g} MB."
        body = json.dumps({"detail": detail}).encode()
        headers = [
            (b"content-type", b"application/json"),
            (b"content-length", str(len(body)).encode()),
        ]
        await send({"type": "http.response.start", "status": 413, "headers": headers})
        await send({"type": "http.response.body", "body": body})
