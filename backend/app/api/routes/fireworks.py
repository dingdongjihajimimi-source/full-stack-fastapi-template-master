import asyncio
import random
from typing import Literal

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(prefix="/fireworks", tags=["fireworks"])

FIREWORK_TYPES = ["classic", "ring", "heavy"]
COLORS = [
    "#FF0000",  # Red
    "#00FF00",  # Green
    "#0000FF",  # Blue
    "#FFFF00",  # Yellow
    "#FF00FF",  # Magenta
    "#00FFFF",  # Cyan
    "#FFA500",  # Orange
    "#800080",  # Purple
    "#FFFFFF",  # White
]


@router.websocket("/stream")
async def stream_fireworks(websocket: WebSocket):
    """
    WebSocket endpoint for streaming real-time fireworks data.
    Acts as a 'Choreographer', sending firework instructions periodically.
    """
    await websocket.accept()
    try:
        while True:
            # 1. Choreographer Logic: Generate random firework parameters
            payload = {
                "x": random.uniform(0, 100),  # Percentage horizontal position
                "y": random.uniform(0, 100),  # Percentage vertical position
                "color": random.choice(COLORS),
                "type": random.choices(
                    FIREWORK_TYPES, weights=[0.6, 0.3, 0.1], k=1
                )[0],  # Weighted random type
                "intensity": random.uniform(0.5, 1.0),  # Explosion intensity
            }

            # 2. Send instruction to client
            await websocket.send_json(payload)

            # 3. Control rhythm (random sleep between 0.1s and 0.5s)
            await asyncio.sleep(random.uniform(0.1, 0.5))

    except WebSocketDisconnect:
        # Gracefully handle client disconnection
        print("Client disconnected from fireworks stream")
    except Exception as e:
        print(f"Error in fireworks stream: {e}")
