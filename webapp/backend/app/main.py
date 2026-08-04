from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.tasks import router as tasks_router
from app.repositories.database import connect, initialize_task_tables
from app.schemas.common import ApiResponse, ok


def create_app() -> FastAPI:
    app = FastAPI(title='JobUWant Web API', version='0.1.0')
    app.add_middleware(
        CORSMiddleware,
        allow_origins=['http://localhost:3000', 'http://127.0.0.1:3000'],
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'],
    )
    app.include_router(tasks_router)

    @app.on_event('startup')
    def _startup() -> None:
        conn = connect()
        try:
            initialize_task_tables(conn)
        finally:
            conn.close()

    @app.get('/api/health', response_model=ApiResponse[dict[str, str]])
    def health() -> ApiResponse[dict[str, str]]:
        return ok({'service': 'jobuwant-web-api', 'status': 'ok'})

    return app


app = create_app()
