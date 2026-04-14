async function render_location_translations(frm) {
	const rows = await frappe.db.get_list("Web Translations", {
		filters: { parent_type: "Locations", parent_id: frm.doc.name },
		fields: ["locale", "translated_field", "translated_value"],
		limit: 500,
	});

	const wrapper = frm.fields_dict.translations_html.$wrapper;

	if (!rows.length) {
		wrapper.html(`<p class="text-muted" style="padding:8px">${__("No translations yet. Click Generate Translations to create them.")}</p>`);
		return;
	}

	let html = `<table class="table table-bordered table-sm" style="margin-top:8px">
		<thead><tr>
			<th>${__("Language")}</th>
			<th>${__("Field")}</th>
			<th>${__("Translated Value")}</th>
		</tr></thead><tbody>`;

	for (const row of rows) {
		html += `<tr>
			<td><b>${frappe.utils.escape_html(row.locale)}</b></td>
			<td>${frappe.utils.escape_html(row.translated_field)}</td>
			<td>${frappe.utils.escape_html(row.translated_value)}</td>
		</tr>`;
	}

	html += `</tbody></table>`;
	wrapper.html(html);
}

frappe.ui.form.on("Locations", {
	async refresh(frm) {
		if (!frm.is_new()) {
			await render_location_translations(frm);
		}

		frm.add_custom_button(__("Generate Translations"), async () => {
			const fields_to_translate = {};
			const val = frm.doc.name;
			if (val) fields_to_translate["name"] = val;

			if (!Object.keys(fields_to_translate).length) {
				frappe.show_alert({ message: __("No field values to translate"), indicator: "orange" }, 4);
				return;
			}

			const langs = await frappe.db.get_list("Available Languages", { fields: ["name"], limit: 100 });
			const target_languages = langs.map((l) => l.name);

			frappe.show_alert({ message: __("Generating translations…"), indicator: "blue" }, 10);

			try {
				const r = await frappe.call({
					method: "frappe_tours.api.translation.generate_translations",
					args: {
						fields: fields_to_translate,
						target_languages: JSON.stringify(target_languages),
					},
				});

				const rows = r.message || [];
				await Promise.all(
					rows
						.filter((row) => row.lang && row.field && row.translated_value)
						.map((row) =>
							frappe.db
								.get_value("Web Translations", {
									locale: row.lang,
									translated_key: row.field,
									parent_type: "Locations",
									parent_id: frm.doc.name,
									translated_field: row.field,
								}, "name")
								.then((res) => {
									const existing = res?.message?.name;
									if (existing) {
										return frappe.db.set_value("Web Translations", existing, "translated_value", row.translated_value);
									}
									return frappe.db.insert({
										doctype: "Web Translations",
										locale: row.lang,
										translated_key: row.field,
										translated_value: row.translated_value,
										parent_type: "Locations",
										parent_id: frm.doc.name,
										translated_field: row.field,
									});
								})
						)
				);

				await render_location_translations(frm);
				frappe.show_alert({ message: __("Translations saved successfully"), indicator: "green" }, 4);
			} catch (err) {
				console.error("Translation error:", err);
				frappe.show_alert({ message: __("Failed to generate translations"), indicator: "red" }, 4);
			}
		});
	},
});
