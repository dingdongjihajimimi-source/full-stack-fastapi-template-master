I will replace the unstable CDN video background with a custom, real-time rendered **Cyber Pixel Starfield** using HTML5 Canvas. This will be implemented as a reusable React component to ensure consistency across both the Dashboard and Chat pages.

### 1. Create Reusable Component
**File:** `frontend/src/components/Common/CyberBackground.tsx` (New File)
- **Technology**: React `useRef` + HTML5 Canvas API.
- **Visual Style**:
  - **Background**: Deep cyber-void gradient (Dark Blue/Purple).
  - **Star System**: 3D starfield effect where stars move towards the viewer (Warp speed effect).
  - **Pixel Aesthetic**: Stars will be rendered as sharp squares (pixels) instead of circles.
  - **Cyber Colors**: A mix of White, Neon Cyan (`#00f3ff`), and Neon Magenta (`#bd00ff`).
  - **Performance**: Optimized animation loop using `requestAnimationFrame`.

### 2. Integrate into Dashboard
**File:** `frontend/src/routes/_layout/index.tsx`
- Remove the `<video>` tag and its source.
- Import and mount `<CyberBackground />` at `z-index: 0`.
- Maintain the existing Fireworks layer on top (`z-index: 50`) - the two canvas effects will coexist (Fireworks in foreground, Starfield in background).

### 3. Integrate into Chat Interface
**File:** `frontend/src/routes/_layout/chat.tsx`
- Remove the `<video>` tag.
- Import and mount `<CyberBackground />` at `z-index: 0`.
- Maintain the existing overlay transparency (`bg-black/60`) to ensure chat text remains readable against the new dynamic background.

### Outcome
- **Stability**: Removes dependency on external CDNs.
- **Aesthetic**: Delivers the requested "Cyber Pixel" look.
- **Performance**: Lightweight real-time rendering.
