from langchain.chat_models import init_chat_model

from .settings import settings

model = init_chat_model(
    model=settings.model_name,
    model_provider=settings.model_provider,
)
