// rendering functions using JQuery

renderMatchSelector = function(h5path) {
	view_div = $("<div></div>");  // create new div for 

	view_div.append($("<h3>").text("Selection"));

	view_div.append($("<span>")
		.attr("title", "Which data matrix to use for analysis? Each data entry could contain multiple matrices.")
		.append($("<label>").text("Matrix"))
		);

	// <span data-tooltip aria-haspopup="true" class="has-tip" title="Download entire project tree.">

	view_div.append($("<select>")
		.attr("class", "medium matrix-select")
		.attr("name", "matrix-select/" + h5path)  // POST name
	);
	// view_div.append("<br><br>");  // spacing

	var matrix_select = view_div.find(".matrix-select");


	// Construct <option> for selecting the matching condition.
	// Later populated with selections from the column names of HDF5/meta_col.
	// The <option> element is then changed by tokenize() yielding a multi selection box
	// with autocomplete.
	view_div.append($("<span>")
		.attr("title", "Which meta data fields to use for matching data? The matching is based on string comparisons generated from the choosen fields.")
		.append($("<label>").text("Sample match condition"))
		);

	view_div.append($("<select>")
		.attr("class", "match-select multi-select")
		.attr("multiple", "multiple")
		.attr("name", "match-select/" + h5path)
		);

	var match_selection_box = view_div.find(".match-select");  // reference

	// Subset select by column option.
	view_div.append($("<span>")
		.attr("title", "Select data subset based on which field?")
		.append($("<label>").text("Sample subset"))
		);
	view_div.append($("<select>")
		.attr("class", "medium subset-select-fields")
		// .attr("name", "subset-select-fields/" + h5path)
		// default
		.append($("<option>")
			.attr("value", "1")  // code for any
			.text("all"))
	);

	var subset_select_field = view_div.find(".subset-select-fields");  // reference

	// Request HDF5 meta data and populate selection form
	$.ajax({
		type: "GET",
		url: "/emmapt/api/h5meta/" + h5path,
		success: function(meta_data) {
			// Create HDF5 selection form

			// Column field names of HDF5 column meta data
			for (var i in meta_data.col_fields) {
				// select match condition
				entry = meta_data.col_fields[i];

				var option = ($("<option>")
					.attr("value", entry)
					.text(entry)
				).appendTo(match_selection_box);

				if ("default_match" in meta_data) {
					// Lookup if the selector entry is default
					if (meta_data.default_match.indexOf(entry) > -1) {
						// default
						option.attr("selected", "");
					} 
				}  // else no defaults

				// Add entry to subset selector
				subset_select_field.append($("<option>")
					.attr("value", entry)
					.text(entry));
			}

			// subset_select_field.prop("selectedIndex", -1);

			// Data matrix names of HDF5 file
			for (var i in meta_data.matrices) {
				entry = meta_data.matrices[i]

				// Add matrix name to selector
				matrix_select.append($("<option>")
					.attr("value", entry)
					.text(entry)
				);
			}

			// Initialize a multi selection box with autocomplete from Tokenize
			// match_sel_box = $("#tokenize").tokenize();  // initialize tokenize
			match_selection_box.tokenize({
				displayDropdownOnFocus: true,
				newElements: false,
				placeholder: "specify match id"
			});

			// specify changes to subset select dropdown on changes
			subset_select_field.on("change", function() {
				// Clear previous
				var subset_select = view_div.find(".subset-select");
				subset_select.remove();

				if (this.value === "1") {
					// terminate without constructing multiselection table
					return 1;
				}

				// Look up value in the meta data
				// Find array number of field name
				var field_index = meta_data.col_fields.indexOf(this.value);

				// Create new multiple selection
				subset_select_field.after(
					$("<select>")
						.attr("class", "subset-select multi-select")
						.attr("multiple", "multiple")
						.attr("name", "subset-select/" + h5path)
					);
				subset_select = view_div.find(".subset-select");  // WARNING: only assigned locally?


				for (var i in meta_data.col_fields_values[field_index]) {
					entry = meta_data.col_fields_values[field_index][i];

					subset_select.append($("<option>")
						.attr("value", entry)
						.text(entry)
						);
				}

				subset_select.tokenize({
					displayDropdownOnFocus: true,
					newElements: false,
					placeholder: "specify samples to include"
				});
			});

		}
	});
	return view_div;
}