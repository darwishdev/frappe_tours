from typing import List, Generic, Protocol, TypeVar, cast
from frappe.model.document import Document

from frappe_tours.pkg.sql.crud_utils import bulk_create_docs, create_or_update_doc

PayloadT = TypeVar("PayloadT")


class AppRepoInterface(Protocol, Generic[PayloadT]):
    def create_or_update(self, payload: PayloadT) -> Document: ...
    def bulk_create(self, payloads: List[PayloadT]) -> List[Document]: ...
class AppRepo(Generic[PayloadT]):
    doc_name: str
    name_key: str
    scalar_fields: List[str]
    child_tables: dict[str, str]

    def __init__(
        self,
        *,
        doc_name: str,
        name_key: str,
        scalar_fields: List[str],
        child_tables: dict[str, str] | None = None,
    ):
        self.doc_name = doc_name
        self.name_key = name_key
        self.scalar_fields = scalar_fields
        self.child_tables = child_tables or {}

    def create_or_update(self, payload: PayloadT) -> Document:
        return create_or_update_doc(
            doctype=self.doc_name,
            name=str(payload.get(self.name_key)),  # type: ignore
            name_key=self.name_key,
            payload=cast(dict, payload),
            scalar_fields=self.scalar_fields,
            child_tables=self.child_tables,
        )

    def bulk_create(self, payloads: List[PayloadT]) -> List[Document]:
        return bulk_create_docs(
            doctype=self.doc_name,
            items=cast(List[dict], payloads),
            name_key=self.name_key,
            scalar_fields=self.scalar_fields,
            child_tables=self.child_tables,
        )
