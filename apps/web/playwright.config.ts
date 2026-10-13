import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "tests",
  timeout: 120000,
  use: {
    baseURL: "http://127.0.0.1:5178",
    viewport: { width: 1440, height: 1000 },
    video: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  reporter: "list",
});
