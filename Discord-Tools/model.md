# Model — Discord-Tools

## Provider

Inference server at `INFERENCE_URL` (e.g. a Cloudflare Tunnel → local llama-server running a quantized Qwen3-8B GGUF).

## Interface

`InferenceClient` (`src/inference_client.py`) is the abstraction layer. The rest of the bot depends only on `InferenceClient.chat()` — swapping the backend requires changing only that class.

Auth uses a rotating API key derived from `INFERENCE_REFRESH_TOKEN` via HMAC-SHA256. Keys are exchanged at `POST /auth/token` and valid for 5-minute windows.

## Parameters (config.py → GENERATION)

| Parameter      | Default |
|---------------|---------|
| max_tokens     | 512     |
| temperature    | 0.6     |
| top_p          | 0.95    |
| top_k          | 20      |
| min_p          | 0.0     |
| repeat_penalty | 1.0     |
| enable_thinking| True    |

## Token Budget

No hard per-call budget enforced on the bot side. The server enforces `max_tokens`. Prompt size is bounded by `max_history_messages` (default 10) × average message length + the tool schema block (~3,500 tokens fixed overhead).

## Constraints

- Timeout: 120 seconds per request (`INFERENCE.timeout`)
- The inference server must be running and reachable; the bot does not fall back to another model
