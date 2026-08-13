from app.core.settings import get_settings
from app.document.mistral_adapter import MistralOcrAdapter


def remote_adapter() -> MistralOcrAdapter:
    return MistralOcrAdapter(get_settings())
