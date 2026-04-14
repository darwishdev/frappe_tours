# Copyright (c) 2026, darwishdev and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class Tours(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from frappe_tours.frappe_tours.doctype.record_files.record_files import RecordFiles
		from frappe_tours.frappe_tours.doctype.tour_program.tour_program import TourProgram

		description: DF.TextEditor | None
		external_transfer_fee: DF.Currency
		from_destination: DF.Link | None
		image: DF.AttachImage | None
		images: DF.Table[RecordFiles]
		included_on_the_package: DF.TextEditor | None
		internal_transfer_fee: DF.Currency
		launch_included: DF.Check
		not_included_on_the_package: DF.TextEditor | None
		price_per_adult: DF.Currency
		price_per_child: DF.Currency
		program: DF.Table[TourProgram]
		to_destination: DF.Link
		tour_guide_included: DF.Check
		transfer_fee: DF.Currency
		transfer_type: DF.Literal["", "Plane", "VAN"]
	# end: auto-generated types

	pass
