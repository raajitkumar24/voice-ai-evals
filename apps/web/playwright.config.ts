import {defineConfig, devices} from "@playwright/test";

export default defineConfig({
  testDir: "../../tests/e2e",
  use: {baseURL: "http://127.0.0.1:3100", trace: "retain-on-failure"},
  webServer: [
    {
      command: "VOICE_EVALS_ENV=test VOICE_EVALS_ENABLE_TEST_PROVIDER=true VOICE_EVALS_DATABASE_URL=sqlite:////private/tmp/voice-evals-e2e.db ../../.venv/bin/uvicorn voice_evals_api.main:app --host 127.0.0.1 --port 8100",
      url: "http://127.0.0.1:8100/health/live",
      reuseExistingServer: !process.env.CI,
    },
    {
      command: "VOICE_EVALS_API_INTERNAL_URL=http://127.0.0.1:8100 pnpm exec next dev -p 3100",
      url: "http://127.0.0.1:3100",
      reuseExistingServer: !process.env.CI,
    },
  ],
  projects: [{name: "chromium", use: {...devices["Desktop Chrome"]}}],
});
