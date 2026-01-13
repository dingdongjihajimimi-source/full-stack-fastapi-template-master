**Analysis**
The user wants to implement a high-performance, real-time fireworks display on the frontend homepage (`frontend/src/routes/_layout/index.tsx`) using HTML5 Canvas. This will be a visual overlay on top of the existing Dashboard content.

**Requirements Breakdown:**
1.  **Canvas Overlay**: A full-screen, transparent canvas (`position: fixed`, `pointer-events: none`) to overlay the dashboard without blocking interactions.
2.  **Particle System**:
    *   Use `useRef` to manage the particle array (avoid `useState` for performance).
    *   Create a `Particle` class/structure with properties: `x`, `y`, `vx`, `vy`, `alpha`, `color`.
    *   Implement physics: Gravity and friction.
    *   Use `requestAnimationFrame` for the rendering loop.
    *   Clean up particles when `alpha <= 0`.
3.  **WebSocket Integration**:
    *   Connect to `/api/v1/fireworks/stream` in `useEffect`.
    *   On message receipt: Parse JSON payload `{x, y, color, type}`.
    *   Convert percentage coordinates (0-100) to screen pixels.
    *   "Explode": Instantiate 50-100 particles at the target location and add them to the `useRef` array.
4.  **Lifecycle Management**:
    *   Ensure WebSocket disconnects and animation loop stops when the component unmounts.

**Implementation Plan:**
1.  **Modify `frontend/src/routes/_layout/index.tsx`**:
    *   Add the `<canvas>` element to the JSX.
    *   Implement the `Particle` class logic (as a helper function or class outside the component, or inside `useEffect`).
    *   Set up the `useEffect` hook for:
        *   Canvas sizing (resize listener).
        *   WebSocket connection.
        *   Animation loop (`requestAnimationFrame`).
    *   Implement the "explosion" logic: When a message arrives, generate particles with random velocities to simulate an explosion.

**Technical Details:**
*   **Coordinate Conversion**: `screenX = (payload.x / 100) * canvas.width`, `screenY = (payload.y / 100) * canvas.height`.
*   **Explosion Physics**: `vx = Math.cos(angle) * speed`, `vy = Math.sin(angle) * speed`.
*   **Update Loop**:
    *   `x += vx`
    *   `y += vy`
    *   `vy += gravity`
    *   `vx *= friction`, `vy *= friction`
    *   `alpha -= decay`

**Refining the Plan:**
I will rewrite `frontend/src/routes/_layout/index.tsx` to include this logic. I'll preserve the existing "Hi, user" welcome message but ensure the canvas sits on top (z-index) but allows clicks through (pointer-events: none).

**Step-by-step:**
1.  Read the current `index.tsx` (already done).
2.  Rewrite `index.tsx` to include the Canvas and Fireworks logic.
3.  Verify that `VITE_API_URL` is used for the WebSocket connection (replacing `http` with `ws`).

**Note on WebSocket URL**: The backend is at `/api/v1/fireworks/stream`. In development, if the frontend is proxied or directly accessing the backend, we need to construct the correct WS URL. Typically `ws://localhost:8000` or relative if proxied. I'll use a robust URL constructor based on `window.location` or `import.meta.env.VITE_API_URL`.