frappe.ui.form.on("Web Page", {});

frappe.ui.form.on("Web Page Block", {
	edit_values(frm, cdt, cdn) {
		console.log("frm", frm);
		return;
	},
});

function open_web_template_values_editor(template, current_values = {}) {
	console.log("open_web_template_values_editor overridden");
	return new Promise((resolve) => {
		frappe.model.with_doc("Web Template", template).then((doc) => {
			let d = new frappe.ui.Dialog({
				title: __("Edit Values"),
				fields: get_fields(doc, () => d),
				primary_action(values) {
					// Re-group flat translation rows → { "DE": [{field, translated_value}], ... }
					const raw_rows = values.translations || [];
					const grouped = {};
					for (const row of raw_rows) {
						if (!row.lang || !row.field) continue;
						const lang = row.lang.trim().toUpperCase();
						if (!grouped[lang]) grouped[lang] = [];
						grouped[lang].push({
							field: row.field,
							translated_value: row.translated_value || "",
						});
					}
					values.translations = grouped;

					// Persist each translation row into Web Translations doctype
					const web_page_name = cur_frm.doc.name;

					const upsert_promises = raw_rows
						.filter((row) => row.lang && row.field && row.translated_value)
						.map((row) => {
							const lang = row.lang.trim().toUpperCase();
							return frappe.db
								.get_value(
									"Web Translations",
									{
										locale: lang,
										translated_key: row.field,
										parent_type: "Web Page",
										parent_id: web_page_name,
										translated_field: row.field,
									},
									"name"
								)
								.then((r) => {
									const existing_name = r?.message?.name;
									if (existing_name) {
										return frappe.db.set_value(
											"Web Translations",
											existing_name,
											"translated_value",
											row.translated_value
										);
									} else {
										return frappe.db.insert({
											doctype: "Web Translations",
											locale: lang,
											translated_key: row.field,
											translated_value: row.translated_value,
											parent_type: "Web Page",
											parent_id: web_page_name,
											translated_field: row.field,
										});
									}
								});
						});

					Promise.all(upsert_promises)
						.then(() => {
							frappe.show_alert(
								{ message: __("Translations saved successfully"), indicator: "green" },
								4
							);
						})
						.catch((err) => {
							console.error("Web Translations save error:", err);
							frappe.show_alert(
								{ message: __("Some translations failed to save"), indicator: "red" },
								4
							);
						});

					d.hide();
					resolve(values);
				},
			});

			$(d.$wrapper).addClass("modal-fullscreen");
			d.$wrapper.find(".modal-dialog").css({
				width: "100vw",
				"max-width": "100vw",
				height: "100vh",
				margin: "0",
			});
			d.$wrapper.find(".modal-content").css({
				height: "100vh",
				"border-radius": "0",
			});
			d.$wrapper.find(".modal-body").css({
				"overflow-y": "auto",
				"max-height": "calc(100vh - 120px)",
			});

			d.set_values(current_values);
			d.show();

			d.sections.forEach((sect) => {
				let fields_with_value = sect.fields_list.filter(
					(field) => current_values[field.df.fieldname]
				);
				if (fields_with_value.length) {
					sect.collapse(false);
				}
			});
		});
	});

	function get_fields(doc, get_dialog) {
		let normal_fields = [];
		let table_fields = [];

		let current_table = null;
		for (let df of doc.fields) {
			if (current_table) {
				if (df.fieldtype != "Table Break") {
					current_table.fields.push(df);
				} else {
					table_fields.push(df);
					current_table = df;
				}
			} else if (df.fieldtype != "Table Break") {
				normal_fields.push(df);
			} else {
				table_fields.push(df);
				current_table = df;
				current_table.fields = [];
			}
		}

		// Build select options from all normal (non-table) field names
		const translatable_fields = normal_fields
			.filter((df) => df.fieldname)
			.map((df) => df.fieldname)
			.join("\n");

		// Parse existing translations from current_values
		// Shape: current_values.translations = { "EN": [{field, translated_value}, ...], ... }
		const existing_translation_rows = [];
		const translations_map = current_values["translations"] || {};
		for (const [lang, entries] of Object.entries(translations_map)) {
			if (Array.isArray(entries)) {
				for (const entry of entries) {
					existing_translation_rows.push({
						lang: lang,
						field: entry.field || "",
						translated_value: entry.translated_value || "",
					});
				}
			}
		}

		const translations_field = {
			label: __("Translations"),
			fieldname: "translations",
			fieldtype: "Table",
			fields: [
				{
					label: __("Language"),
					fieldname: "lang",
					fieldtype: "Link",
					options: "Available Languages",
					in_list_view: 1,
					columns: 2,
				},
				{
					label: __("Field"),
					fieldname: "field",
					fieldtype: "Select",
					options: translatable_fields,
					in_list_view: 1,
					columns: 3,
				},
				{
					label: __("Translated Value"),
					fieldname: "translated_value",
					fieldtype: "Text Editor",
					in_list_view: 0,
					columns: 5,
				},
			],
			data: existing_translation_rows,
			get_data: () => existing_translation_rows,
		};

		const generate_translations_button = {
			label: __("Generate Translations"),
			fieldname: "generate_translations",
			fieldtype: "Button",
			async click() {
				const dialog = get_dialog();
				const values = dialog.get_values();

				// Build { fieldname: value } for all translatable fields that have a value
				const fields_to_translate = {};
				for (const field of translatable_fields.split("\n")) {
					if (!field) continue;
					const val = values[field];
					if (val && typeof val === "string") {
						fields_to_translate[field] = val;
					}
				}

				if (!Object.keys(fields_to_translate).length) {
					frappe.show_alert({ message: __("No field values to translate"), indicator: "orange" }, 4);
					return;
				}

				const langs = await frappe.db.get_list("Available Languages", {
					fields: ["name"],
					limit: 100,
				});
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
					dialog.fields_dict.translations.df.data = rows;
					dialog.fields_dict.translations.grid.refresh();
					frappe.show_alert({ message: __("Translations generated"), indicator: "green" }, 4);
				} catch (err) {
					console.error("Translation error:", err);
					frappe.show_alert({ message: __("Failed to generate translations"), indicator: "red" }, 4);
				}
			},
		};

		return [
			...normal_fields,
			...table_fields.map((tf) => {
				let data = current_values[tf.fieldname] || [];
				return {
					label: tf.label,
					fieldname: tf.fieldname,
					fieldtype: "Table",
					fields: tf.fields.map((df, i) => ({
						...df,
						in_list_view: i <= 1,
						columns: tf.fields.length == 1 ? 10 : 5,
					})),
					data,
					get_data: () => data,
				};
			}),
			translations_field,
			generate_translations_button,
		];
	}
}
