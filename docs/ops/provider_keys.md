# Provider API Keys

Commercial provider credentials are **user-scoped** and must be entered in the app’s **Profile → Provider Keys** section. These keys are stored per user and unlock provider models for that user. Do **not** put commercial provider keys in server env vars.

For detailed, step-by-step instructions (with links), see [docs/ops/user_provider_credentials.md](docs/ops/user_provider_credentials.md).


## OpenAI
1. Create an API key at https://platform.openai.com/account/api-keys
2. Paste it into Profile → OpenAI.

## Anthropic
1. Create an API key at https://console.anthropic.com/account/keys
2. Paste it into Profile → Anthropic.

## Google (Gemini)
1. Create a Gemini API key at https://aistudio.google.com/app/apikey
2. Paste it into Profile → Google AI.

## Microsoft (Azure OpenAI)
1. Create an Azure OpenAI resource: https://portal.azure.com
2. Deploy a model and note the **deployment name**.
3. Copy the API key and endpoint URL from the resource.
4. Paste key + endpoint into Profile → Azure OpenAI.

## xAI
1. Create an API key at https://console.x.ai/
2. Paste it into Profile → xAI.

## DeepSeek
1. Sign in at https://platform.deepseek.com/
2. Go to **API Keys** (left sidebar) and click **Create new secret key**.
3. Copy the key — it is only shown once.
4. Paste it into Profile → Provider Keys → **DeepSeek**.

## Local Testing Models (recommended)
For local runtimes, pick one model per modality:
- **Text**: llama.cpp (GGUF) — simple CPU/GPU testing.
- **Image**: Stable Diffusion via diffusers.
- **3D**: Shap-E (text-to-3d) for a lightweight baseline.

These are used by the LocalRunner integration and can be swapped later.