"""AWS Lambda entry point — Mangum ASGI adapter for the FastAPI app."""

from mangum import Mangum

from server.main import app

handler = Mangum(app, lifespan="off")
