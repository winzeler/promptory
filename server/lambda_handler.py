"""AWS Lambda entry point — Mangum ASGI adapter for the FastAPI app."""

import os

from mangum import Mangum

from server.main import app

# HTTP API v2 with a named stage includes the stage prefix in rawPath.
# Mangum must strip it so FastAPI sees the correct route.
stage = os.environ.get("STAGE", "")
base_path = f"/{stage}" if stage else ""

handler = Mangum(app, lifespan="auto", api_gateway_base_path=base_path)
