**Analysis**
The user wants to implement a high-performance, real-time fireworks show for the homepage.

1. **Backend Implementation**:

   * **New Route**: Need to create `backend/app/api/routes/fireworks.py`.

   * **WebSocket Endpoint**: Implement `ws /api/v1/fireworks/stream`.

   * **Choreographer Logic**: Inside the WebSocket handler, run an infinite loop (`while True`) that:

     * Sleeps for a random interval (0.1s - 0.5s).

     * Generates a random firework instruction (x, y, color, type, intensity).

     * Sends this JSON data to the client.

   * **Connection Management**: Handle `WebSocketDisconnect` gracefully.

   * **Router Registration**: Register the new router in `backend/app/api/main.py`.

**Plan**

1. **Create** **`backend/app/api/routes/fireworks.py`**:

   * Import necessary modules (`APIRouter`, `WebSocket`, `WebSocketDisconnect`, `random`, `asyncio`).

   * Define the `router`.

   * Implement the `stream_fireworks` WebSocket endpoint.

   * Add the "Choreographer Logic" to generate random firework data.

2. **Modify** **`backend/app/api/main.py`**:

   * Import the new `fireworks` router.

   * Include it in `api_router` with the prefix `/fireworks` and tag `fireworks`.

3. **Verify**:

   * Restart the backend container to apply changes.

   * (Self-check) The user asked for "only backend modification" in the first step prompt ("首先请修改后端..."), so I will focus on the backend implementation as requested.

**Note**: The user specifically provided the "Choreographer Logic" requirements (x, y, color, type, intensity). I will ensure the Python code implements this exactly.

**Step-by-step Implementation Plan:**

1. Create the file `backend/app/api/routes/fireworks.py` with the WebSocket logic.
2. Update `backend/app/api/main.py` to register the new route.
3. Restart the backend service.

