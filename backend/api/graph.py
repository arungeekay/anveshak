"""Graph query endpoint (contracts.md §6)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..db import get_connection
from ..graph import engine

router = APIRouter()


class GraphQuery(BaseModel):
    type: str  # path_between | ego_network | community_of
    params: dict = {}


@router.post("/api/graph/query")
def graph_query(q: GraphQuery) -> dict:
    try:
        return engine.query(get_connection(), q.type, q.params)
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/graph/rebuild")
def rebuild() -> dict:
    engine.cache.rebuild(get_connection())
    return {"nodes": engine.cache.g.number_of_nodes(),
            "communities": len(engine.cache.comms or [])}
