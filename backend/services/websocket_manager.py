import asyncio
from dataclasses import dataclass
from typing import Any


@dataclass
class WebSocketConnection:
    loop: asyncio.AbstractEventLoop
    queue: asyncio.Queue[dict[str, Any]]


class WebSocketManager:
    def __init__(self):
        self._connections: dict[str, list[WebSocketConnection]] = {}

    def connect(self, session_id: str) -> WebSocketConnection:
        connection = WebSocketConnection(
            loop=asyncio.get_running_loop(),
            queue=asyncio.Queue(),
        )
        self._connections.setdefault(session_id, []).append(connection)
        return connection

    def disconnect(self, session_id: str, connection: WebSocketConnection) -> None:
        connections = self._connections.get(session_id)
        if not connections:
            return
        if connection in connections:
            connections.remove(connection)
        if not connections:
            self._connections.pop(session_id, None)

    def broadcast(self, session_id: str, payload: dict[str, Any]) -> None:
        # REST 处理器是同步的，因此事件投递调度到每个 socket 的事件循环上。
        for connection in list(self._connections.get(session_id, [])):
            connection.loop.call_soon_threadsafe(connection.queue.put_nowait, payload)
