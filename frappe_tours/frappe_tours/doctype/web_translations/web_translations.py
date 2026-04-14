# Copyright (c) 2026, darwishdev and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class WebTranslations(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		locale: DF.Link
		parent_id: DF.Data
		parent_type: DF.Data
		translated_field: DF.Data
		translated_key: DF.Data
		translated_value: DF.TextEditor
	# end: auto-generated types

	pass
