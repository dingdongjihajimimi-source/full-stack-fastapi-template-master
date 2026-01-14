I will implement the frontend "AI SQL Generator" page incrementally, ensuring it matches the existing project structure and style.

### 1. Update API Client
- **Action**: Run `npm run generate-client` inside the `frontend` container/directory. This will automatically update `frontend/src/client` with the new `/crawl/start` and `/crawl/{task_id}` endpoints defined in the backend OpenAPI schema.
- **Why**: This is cleaner than manually adding methods and ensures type safety.

### 2. Create Crawler Page
- **New File**: `frontend/src/routes/_layout/crawler.tsx`
- **Route**: `/_layout/crawler`
- **Components**:
  - **Header**: Title "AI SQL Generator".
  - **Action Area**: A large "Start AI Crawling" button.
    - **State**: `isLoading` (boolean) to toggle button loading state.
    - **Logic**: On click, call `CrawlerService.startCrawl()`.
  - **Progress Area**:
    - **Logic**: Upon getting a `task_id`, use `useQuery` (with `refetchInterval`) or `setInterval` to poll `CrawlerService.getCrawlStatus(taskId)`.
    - **Condition**: Stop polling when status is `completed` or `failed`.
  - **Result Area**:
    - Display the SQL result in a `<pre>` block or a CodeBlock component styled with Tailwind (e.g., `bg-gray-900 text-green-400 p-4 rounded`).

### 3. Update Sidebar
- **File**: `frontend/src/components/Sidebar/AppSidebar.tsx`
- **Action**: Add the new route to `baseItems`.
  - **Icon**: Use `Database` or `Bot` from `lucide-react`.
  - **Title**: "AI SQL Generator".
  - **Path**: "/crawler".

### 4. Build & Verify
- Rebuild the frontend container to apply changes if necessary (though React HMR should handle it).
- Verify the flow: Click Button -> Loading -> Polling -> Display SQL.
