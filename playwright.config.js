const { defineConfig, devices } = require("@playwright/test");

const PORT = 4173;

module.exports = defineConfig({
  testDir: "tests",
  // One worker keeps the scroll budget from competing with other tests for CPU.
  workers: 1,
  forbidOnly: !!process.env.CI,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: `http://localhost:${PORT}`,
    trace: "retain-on-failure",
  },
  webServer: {
    command: `python3 -m http.server ${PORT}`,
    url: `http://localhost:${PORT}/index.html`,
    reuseExistingServer: !process.env.CI,
    stderr: "ignore",
  },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 } },
    { name: "mobile", use: { ...devices["Pixel 7"] } },
  ],
});
