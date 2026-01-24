# Provider API Keys

This project supports multiple commercial providers. Store keys in a .env file (see .env.example). Never commit real keys. Requests to a provider will fail if its API key is missing.


## OpenAI
1. Create an account at https://platform.openai.com
2. Go to **API Keys**.
3. Create a new secret key.
4. Set `LLM_API_OPENAI_API_KEY`.

## Anthropic
1. Create an account at https://console.anthropic.com
2. Go to **API Keys**.
3. Create a new key.
4. Set `LLM_API_ANTHROPIC_API_KEY`.

## Google (Gemini)
1. Create a project in Google Cloud Console: https://console.cloud.google.com
2. Enable **Generative Language API**.
3. Create an API key.
4. Set `LLM_API_GOOGLE_API_KEY`.

## Microsoft (Azure OpenAI)
1. Create an Azure OpenAI resource: https://portal.azure.com
2. Deploy a model and note the **deployment name**.
3. Copy the API key and endpoint URL from the resource.
4. Set:
   - `LLM_API_AZURE_OPENAI_API_KEY`
   - `LLM_API_AZURE_OPENAI_ENDPOINT`
   - `LLM_API_AZURE_OPENAI_API_VERSION`

## xAI
1. Create an account at https://x.ai
2. Create an API key in the console.
3. Set `LLM_API_XAI_API_KEY`.

## Local Testing Models (recommended)
For local runtimes, pick one model per modality:
- **Text**: llama.cpp (GGUF) — simple CPU/GPU testing.
- **Image**: Stable Diffusion via diffusers.
- **3D**: Shap-E (text-to-3d) for a lightweight baseline.

These are used by the LocalRunner integration and can be swapped later.