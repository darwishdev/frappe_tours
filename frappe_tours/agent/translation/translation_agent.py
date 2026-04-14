from google import genai
from google.genai import types
from frappe_tours.agent.translation.types import TranslationOutput
from frappe_tours.agent.translation.instructions import TRANSLATION_SYSTEM_INSTRUCTION


class TranslationAgent:
    def __init__(self, client: genai.Client, model_name: str):
        self.client = client
        self.model_name = model_name

    def run(self, fields: dict[str, str], target_languages: list[str]) -> list[dict]:
        fields_text = "\n".join(f"- {k}: {v}" for k, v in fields.items())
        langs_text = ", ".join(target_languages)

        prompt = (
            f"Translate the following field values into these languages: {langs_text}\n\n"
            f"Fields to translate:\n{fields_text}"
        )

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=TRANSLATION_SYSTEM_INSTRUCTION,
                temperature=0.2,
                response_mime_type="application/json",
                response_schema=TranslationOutput,
            ),
        )

        output: TranslationOutput = response.parsed

        rows = []
        for lang_translation in output.translations:
            for field_translation in lang_translation.fields:
                rows.append({
                    "lang": lang_translation.lang,
                    "field": field_translation.field,
                    "translated_value": field_translation.translated_value,
                })
        return rows
