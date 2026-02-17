from llm_api.config import get_settings


def get_default_model() -> str:
    settings = get_settings()
    return settings.default_model
