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
1. Create a **Read** token (scopes: **read**).
2. If you plan to use gated models (e.g., Llama 3), open the model page and **request access / accept the license terms**.
3. In Profile → Hugging Face, paste the token.

Hugging Face tokens are used for downloading local models from the Models page. For gated models, a valid token alone is not enough—you must also be granted access and accept the model’s license on Hugging Face first.

### Using gated models (Llama 3, etc.)
Gated models require two things:
1. **Access approval + license acceptance** on the model’s Hugging Face page.
2. A **Hugging Face Read token** saved in Profile → Hugging Face.

**Step‑by‑step**
1. Open the model page on Hugging Face (example: Llama 3).
2. Click **Request access** (or **Agree and access**), then accept the license terms.
3. Wait for approval if required (some models approve instantly; others require manual approval).
4. In this app, go to **Profile → Provider Keys → Hugging Face** and paste your **Read** token.
5. Return to **Models** and refresh. The gated model should now download or load normally.

**If you still see an access error**
- Confirm you are signed in on Hugging Face with the **same account** that generated the token.
- Verify the token has **read** scope and has not expired or been revoked.
- Revisit the model page to ensure the license is accepted for your account.

**In‑app guidance**
When a gated model is requested without access, the app should prompt:
- “This model is gated on Hugging Face. Please request access and accept the license terms on the model page, then try again.”
