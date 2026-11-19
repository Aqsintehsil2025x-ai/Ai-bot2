# XFA AI providers

XFA uses operator-managed API credentials only. Provider keys are read on the server and are never returned by the provider catalogue endpoint.

## Supported providers

| Provider | Secret name | Default model | Cost / access note |
|---|---|---|---|
| Google Gemini | `GEMINI_API_KEY` (or legacy `GOOGLE_API_KEY`) | `gemini-3.8-flash` | Account-specific quota and model availability |
| NVIDIA NIM | `NVIDIA_API_KEY` | `meta/llama-3.3-70b-instruct` | Model access and limits depend on the NVIDIA account |
| Groq | `GROQ_API_KEY` | `openai/gpt-oss-120b` | Developer-tier limits vary by account and model |
| OpenRouter | `OPENROUTER_API_KEY` | `openrouter/free` | Free routing is rate-limited; the selected underlying model can change |
| DeepSeek | `DEEPSEEK_API_KEY` | `deepseek-flash` | Paid token usage; check current pricing and balance before enabling |

The catalogue is intentionally conservative. It lists only model IDs verified against the provider documentation at implementation time; providers can change availability without notice.

## Configure credentials

Add only the providers you intend to use to the **backend runtime's** secret/environment settings. Do not put credentials in the dashboard, browser storage, Git, or any `VITE_*` variable.

For the current Flask deployment, set these in the backend host's runtime secrets. Cloudflare Pages hosting the static dashboard does not automatically pass its secrets to the separate Flask backend.

## Safety and cost controls

- XFA does not silently switch a user's selected provider to another provider.
- A provider is shown as connected only when its server-side secret exists.
- OpenRouter's `openrouter/free` route can select among available free models; availability and limits are controlled by OpenRouter and upstream providers.
- DeepSeek is marked as paid. Do not enable it unless the operator intentionally configures a funded API account.
- Never log or return API keys or raw provider error bodies.
