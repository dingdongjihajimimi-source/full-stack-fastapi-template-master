**Analysis**
The user is experiencing a visual overlap issue where the Chat Sidebar (specifically the "New Chat" button area) scrolls up and slides *under* or *into* the Global Header area (where the Sidebar Trigger is). This happens because the Chat component's height (`h-[calc(100vh-4rem)]`) is set too tall relative to its container (which has padding), forcing the entire page to scroll. When the page scrolls, the "New Chat" button moves up and collides with the sticky header.

**Plan**

1. **Fix Container Height**: Reduce the height of the chat container in `frontend/src/routes/_layout/chat.tsx` to prevent the main page from scrolling.

   * Change `h-[calc(100vh-4rem)]` to `h-[calc(100vh-12rem)]`. This accounts for the Global Header, Page Padding, and Footer, ensuring the chat interface fits entirely within the viewport without triggering global scrolling.
2. **Verify**: Ensure the chat content scrolls *internally* (within its own container) while the "New Chat" button remains fixed and distinct from the Global Header.

**Changes**

* Modify `frontend/src/routes/_layout/chat.tsx`: Update the root `div` height class.

