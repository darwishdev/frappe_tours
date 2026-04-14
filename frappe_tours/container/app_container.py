from google.genai.client import Client
from frappe_tours.agent.translation.translation_agent import TranslationAgent


class AppContainer:
    translation_agent: TranslationAgent

    def __init__(self, gemini_api_key: str):
        model_name = "gemini-2.5-flash-lite"
        gemini_client = Client(api_key=gemini_api_key)
        self.translation_agent = TranslationAgent(client=gemini_client, model_name=model_name)
