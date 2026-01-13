**Analysis**
The user provided feedback that adding a second `SidebarTrigger` to the chat sidebar created a redundant button and didn't solve the visual overlap issue cleanly. The original issue was that the "New Chat" button in the local chat sidebar was positioned too close to the top of the content area, visually conflicting with the global Sidebar Trigger located in the header immediately above it.

**Plan**
1.  **Revert Redundancy**: Remove the `SidebarTrigger` component and its import from `frontend/src/routes/_layout/chat.tsx` to eliminate the duplicate button.
2.  **Fix Spacing**: Add a top margin (`mt-4` or `pt-4`) to the container of the "New Chat" button or the sidebar itself. This will push the local sidebar content down, creating a visual buffer between the global header (where the main trigger lives) and the local chat controls.
3.  **Verify**: Rebuild the frontend to ensure the layout is clean and the "New Chat" button is easily clickable without interference.

**Changes**
*   Modify `frontend/src/routes/_layout/chat.tsx`:
    *   Remove `<SidebarTrigger />`.
    *   Add spacing (e.g., `className="mt-4"`) to the "New Chat" button's wrapper or the button itself.