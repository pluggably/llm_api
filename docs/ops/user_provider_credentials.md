# User Provider Credentials (Profile-Based)

This app uses **user-provided credentials** stored in the Profile page. Once a user saves a provider key, the corresponding commercial models appear in the Models screen and can be used for chat.

## Where to add keys in the app
1. Open **Profile** in the left nav.
2. Scroll to **Provider Keys**.
3. Expand a provider card, paste the credentials, and click **Save**.
4. Return to **Models** — provider models will appear automatically.

> Tip: If models do not appear immediately, refresh the Models page.

---

## OpenAI
**Create key**: https://platform.openai.com/account/api-keys
1. Create a new secret key.
2. In Profile → OpenAI, paste the key.

**Models unlocked (default list)**:
- GPT-4o mini (`gpt-4o-mini`)
- GPT-4o (`gpt-4o`)

---

## Anthropic
**Create key**: https://console.anthropic.com/account/keys
1. Create a new API key.
2. In Profile → Anthropic, paste the key.

**Models unlocked (default list)**:
- Claude 3.5 Sonnet (`claude-3-5-sonnet`)
- Claude 3.5 Haiku (`claude-3-5-haiku`)

---

## Google (Gemini)
**Create key**: https://aistudio.google.com/app/apikey
1. Create a Gemini API key.
2. In Profile → Google AI, paste the key.

**Models unlocked (default list)**:
- Gemini 1.5 Flash (`gemini-1.5-flash`)
- Gemini 1.5 Pro (`gemini-1.5-pro`)

---

## xAI
**Create key**: https://console.x.ai/
1. Create an API key.
2. In Profile → xAI, paste the key.

**Models unlocked (default list)**:
- Grok 2 (`grok-2`)
- Grok 2 Mini (`grok-2-mini`)

---

## Azure OpenAI
**Create resource**: https://portal.azure.com/
1. Create an **Azure OpenAI** resource.
2. Deploy a model and note the **deployment name**.
3. Copy the **endpoint URL** and **API key** from the resource.
4. In Profile → Azure OpenAI, paste the endpoint + key.

**Using Azure models**
Azure uses your **deployment name** as the model ID. In this UI, Azure models are not auto-listed. You can still call them by model ID using the API or by adding them via the registry in the backend.

---

## Hugging Face (optional)
**Create token**: https://huggingface.co/settings/tokens
1. Create a **Read** token.
2. In Profile → Hugging Face, paste the token.

Hugging Face tokens are used for downloading local models from the Models page.
