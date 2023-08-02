from fastapi import APIRouter, Depends, WebSocket
from starlette.routing import WebSocketRoute
from .views import wsuser, wsagent

router = APIRouter(
    prefix="/ws",
    tags=["ws"],
    responses={404: {"description": "Not found"}},
)

wsroutes = [
    # WebSocketRoute("/ws/wsss/", websocket_endpoint),
    WebSocketRoute("/ws/user/", wsuser),
    WebSocketRoute("/ws/agent/", wsagent)
]
