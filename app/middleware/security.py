class SecurityHeadersMiddleware:
    def __init__(self, app):
        self.app = app
        self._headers = [
            (b"x-content-type-options", b"nosniff"),
            (b"x-frame-options", b"DENY"),
            (b"x-xss-protection", b"1; mode=block"),
            (b"strict-transport-security", b"max-age=31536000; includeSubDomains"),
            (b"content-security-policy", b"default-src 'none'"),
            # 🛡️ Sentinel: Instruct browsers not to send the Referer header to prevent leaking application URLs
            (b"referrer-policy", b"no-referrer"),
            # 🛡️ Sentinel: Prevent caching of API responses
            (b"cache-control", b"no-store, no-cache, must-revalidate, max-age=0"),
            # 🛡️ Sentinel: Mask the 'server' header to prevent technology stack information disclosure (Uvicorn adds it if omitted)
            (b"server", b"hidden"),
            # 🛡️ Sentinel: Restrict browser features via Permissions-Policy to prevent access to sensitive APIs
            (b"permissions-policy", b"accelerometer=(), camera=(), geolocation=(), gyroscope=(), magnetometer=(), microphone=(), payment=(), usb=()"),
            # 🛡️ Sentinel: Prevent cross-origin resource sharing and cross-origin window opening for API isolation
            (b"cross-origin-resource-policy", b"same-origin"),
            (b"cross-origin-opener-policy", b"same-origin"),
            # 🛡️ Sentinel: Ensure cross-origin isolation by requiring Cross-Origin-Resource-Policy for embeddings
            (b"cross-origin-embedder-policy", b"require-corp")
        ]

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                # Ensure compliance with ASGI spec (list of tuples)
                headers = list(message.get("headers", []))
                # Remove existing 'server' headers to prevent duplicates
                headers = [h for h in headers if h[0].lower() != b"server"]
                headers.extend(self._headers)
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_wrapper)
