# Copyright (c) 2026, darwishdev and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class TourReservation(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		adults: DF.Int
		children: DF.Int
		client_name: DF.Data | None
		include_external_transfer: DF.Check
		include_internal_transfer: DF.Check
		infants: DF.Int
		price_per_adult: DF.Currency
		price_per_child: DF.Currency
		reservation_date: DF.Data | None
		total_price: DF.Currency
		tour: DF.Link | None
	# end: auto-generated types

	pass
