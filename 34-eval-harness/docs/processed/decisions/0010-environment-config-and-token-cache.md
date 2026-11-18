# 0010 Environment-variable settings everywhere; a local launcher and token cache; any OpenAI-compatible model

- **Status:** Accepted, 7 Nov 2026
- **Context:** On the course platform, the runner gives settings as environment variables and never shows a password. We want local runs to behave the same. Teammates use different model providers, and the platform's model is different again.
- **Decision:**
  - **No local mode.** The eval harness and the agent read only process environment variables, and never read `.env` or log in.
  - **The launcher.** Locally, `scripts/run_local.py` gets a token from `scripts/local_auth.py`, sets the same `AGENTSWITCH_*` variables the runner sets, and starts the harness as the runner would.
  - **The token cache.** `local_auth.py` reuses the token cached in `TOKEN_CACHE_DIR` while it still works. Otherwise it logs in once with `AS_EMAIL` and `AS_<SYSTEM>_PASSWORD` from `.env`. It never retries a refused login.
  - **The model.** Any OpenAI-compatible provider, through the `openai` SDK's own variables (`OPENAI_BASE_URL`, `OPENAI_API_KEY`, `OPENAI_PROJECT_ID`), plus the course's `OPENAI_MODEL`. That can be one model, or a comma-separated list tried in order.
  - **Provider quirks** go in the optional `OPENAI_EXTRA_BODY` (JSON), not in code.
- **Consequences:**
  - One set of variable names serves every person and the platform.
  - Passwords are used about once a week per system.
  - The token cache and `.env` are git-ignored; settings errors name the variables, never their values.
