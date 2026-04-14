from pydantic import BaseModel, Field
from typing import List


class FieldTranslation(BaseModel):
    field: str = Field(description="The field name exactly as provided in the input")
    translated_value: str = Field(description="The translated text for this field in the target language")


class LanguageTranslation(BaseModel):
    lang: str = Field(description="The language code exactly as provided (e.g. EN, AR, FR, DE)")
    fields: List[FieldTranslation] = Field(description="Translations for every field in this language")


class TranslationOutput(BaseModel):
    translations: List[LanguageTranslation] = Field(
        description="One entry per target language, each containing translations for all fields"
    )
