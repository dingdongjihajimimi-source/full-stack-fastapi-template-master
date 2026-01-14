I have identified the cause of the build error: the `CrawlerStartCrawlData` type is defined in `types.gen.ts` but is missing from the import list in `sdk.gen.ts`.

Here is the plan to fix it:

1. **Update** **`frontend/src/client/sdk.gen.ts`**:

   * Add `CrawlerStartCrawlData` to the named imports from `./types.gen`.

2. **Verify the Build**:

   * Run `npm run build` in the `frontend` directory to ensure the TypeScript error is resolved and the application builds successfully.

3. **Deployment Check**:

   * Once the build passes locally, I will confirm that the fix is ready for deployment.

