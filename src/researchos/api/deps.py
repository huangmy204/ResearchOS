from __future__ import annotations

from fastapi import Request

from researchos.api.services import AppServices


def get_services(request: Request) -> AppServices:
    return request.app.state.services
