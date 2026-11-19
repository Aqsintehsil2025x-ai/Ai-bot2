# Discord bot AI providers

The Discord bot supports the following server-managed providers. Add only the secrets you plan to use to the bot's backend runtime environment (Replit, Render, or another process host).

| Provider | Secret | Default model | Notes |
|---|---|---|---|
| Google Gemini | `GEMINI_API_KEY` or `GOOGLE_API_KEY` | `gemini-3.5-flash-lite` | Account-specific quotas and model access |
| NVIDIA NIM | `NVIDIA_API_KEY` | `nvidia/nemotron-3.5-super-vl-120b-a12b` | Account/model access may vary |
| OpenAI | `OPENAI_API_KEY` | `gpt-6-astra` | Paid API usage may apply |
| Groq | `GROQ_API_KEY` | `openai/gpt-oss-120b` | Developer-tier rate limits are account-specific |
| OpenRouter | `OPENROUTER_API_KEY` | `openrouter/free` | Free routing is rate-limited and upstream availability varies |
| DeepSeek | `DEEPSEEK_API_KEY` | `deepseek-flash` | Paid token usage; check balance and pricing |

## Provider commands

Server administrators (or configured sovereign owners) can select the server's provider with `/gemini`, `/gemma`, `/nvidia`, `/openai`, `/groq`, `/openrouter`, or `/deepseek`.

The new Groq, OpenRouter, and DeepSeek adapters currently support text chat. Image requests continue to use providers with an explicit image path; the bot returns a clear message rather than sending an unsupported image request.

## Security

- Never put provider keys in source files, Discord messages, command arguments, or public logs.
- No automatic cross-provider fallback is used, so a selected paid provider cannot silently charge through a different account.
- DeepSeek is paid. Configure it only if the operator intentionally enables a funded API account.
