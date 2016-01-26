// File tree manipulations and rendering

// Draws tree on provided a D3 svg object that is styled to deterimen the svg width and height.
// info_panel is a div pointer to where 
function drawTree(svg, data, info_div) {

	// Get SVG dimensions from style.
	var width = parseInt(svg.style('width'), 10);  // removes "px"
	var height = parseInt(svg.style('height'), 10);


	// Make svg group for elements
	var svg_group = svg.append("g")
		.attr("transform", "translate(30,6)");

	// Diagonal generator
	var diagonal = d3.svg.diagonal()
		.projection(function(d) { return [d.y, d.x]; });  // x and y are swapped

	// Initialize d3 layout
	var tree = d3.layout.tree()
		.size([height, width - 120]);

	// Init nodes and edges.
	var nodes = tree.nodes(data),
		links = tree.links(nodes);

	var link = svg_group.selectAll("path.link")
		.data(links)
	.enter().append("path")
		.attr("class", "link")
		.attr("d", diagonal);

	var node = svg_group.selectAll("g.node")
		.data(nodes)
	.enter().append("g")
		.attr("class", "node")
		.attr("transform", function(d) { return "translate(" + d.y + "," + d.x + ")"; })

	node.append("circle")
		.attr("r", 4.5);

	node.append("text")
		// .attr("dx", function(d) { return d.children ? -8 : 8; })
		// .attr("dx", function(d) { return 8; })
		.attr("dx", -4)
		.attr("dy", -6)
		.attr("class", "label")
		// .attr("text-anchor", function(d) { return d.children ? "end" : "start"; })
		.text(function(d) { return d.name; });

	if (typeof info_div !== "undefined") {
		// info <div> provided
		updateInfo(info_div, data);  // default rendering of info panel. root data tree passed.

		// Clicking nodes in the tree, callback function.
		node.on("click", function(d) {
			// window.location = "/emmapt/" + d.path;  // load file using the emmapt/dtree interface


			// Unselect everything except the node clicked
			var self = this;  // the node clicked, JS reference
			svg_group.selectAll("g.node")
				.filter(function(x) {return self != this;})
				.classed("selected", false);

			// Toogle clicked class for selected node
			var this_node = d3.select(this);  // shortcut, D3 reference
			this_node.classed("selected", !this_node.classed("selected"));

			// Update the info bar based on the node class selection.
			// updateInfo(svg, info_div, default_meta);

			// Update info <div>
			if (this_node.classed("selected")) {
				//
				updateInfo(info_div, d);  // passing the node data 
			} else {
				// default visualization, no node is selected
				updateInfo(info_div, data);  // root tree passed as default
			}
		});

		// node.on("mouseover", function(d) {
		// 	// d3.select(this).style({})
		// });
	}
}

// Updates info panel of tree selection according to data provided in item.
// The item can be the root of a project tree. Visualization bechaviour is 
// determined by item.type.
function updateInfo(info_div, item) {
	info_div.empty();  // clear previous info <div>

	// Title of info panel
	// info_div.append($("<h3>").text(item.path));

	// Alternative rendering for different item types.
	if (item.type === "dir") {
		// render json meta data, read server-side from dir/meta.json.
		var node = new PrettyJSON.view.Node({
		  el: info_div,  // DOM element that gets filled in
		  data: item.meta
		});
	} else if (item.type === "file") {
		// General/generic file, show type and size

		// info_div.html("file " + item.path);
		// info_div.append(item.size/1000000 + " MB");
		info_div.append((item.size/1000000).toFixed(3) + " MB");

		// Action bar
		info_div.append(
			$("<div>").attr("class", "row")
				.append($("<div>").attr("class", "column text-right")
					.append($("<a>")
						.attr("class", "text-right")
						.attr("href", "/emmapt/download/" + item.path)
						.text("download")
					)
					.append(" ")
					.append($("<a>")
						.attr("href", "/emmapt/" + item.path)
						.text("view")
					)
				)
			);

	} else if (item.type === "hdf5") {

		info_div.append((item.size/1000000).toFixed(3) + " MB");

		// HDF5 files, load additional selectors
		// Action bar
		info_div.append(
			$("<div>").attr("class", "row")
				.append($("<div>").attr("class", "column text-right")
					.append($("<a>")
						.attr("class", "text-right")
						.attr("href", "/emmapt/download/" + item.path)
						.text("download")
					)
					.append(" ")
					.append($("<a>")
						.attr("href", "/emmapt/" + item.path)
						.text("view")
					)
				)
			);

		info_div.append($("<h3>").text("Selection"))

		info_div.append($("<span>")
			.attr("title", "Which data matrix to use for analysis? Each data entry could contain multiple matrices.")
			.append($("<label>").text("Matrix"))
			);

		// <span data-tooltip aria-haspopup="true" class="has-tip" title="Download entire project tree.">

		info_div.append($("<select>")
			.attr("class", "medium matrix-select")
			.attr("name", "matrix-select/" + item.path)  // POST name
		);
		// info_div.append("<br><br>");  // spacing

		var matrix_select = info_div.find(".matrix-select");


		// Construct <option> for selecting the matching condition.
		// Later populated with selections from the column names of HDF5/meta_col.
		// The <option> element is then changed by tokenize() yielding a multi selection box
		// with autocomplete.
		info_div.append($("<span>")
			.attr("title", "Which meta data fields to use for matching data? The matching is based on string comparisons generated from the choosen fields.")
			.append($("<label>").text("Sample match condition"))
			);

		info_div.append($("<select>")
			.attr("class", "match-select multi-select")
			.attr("multiple", "multiple")
			.attr("name", "match-select/" + item.path)
			);

		var match_selection_box = info_div.find(".match-select");  // reference

		// Subset select by column option.
		info_div.append($("<span>")
			.attr("title", "Select data subset based on which field?")
			.append($("<label>").text("Sample subset"))
			);
		info_div.append($("<select>")
			.attr("class", "medium subset-select-fields")
			// .attr("name", "subset-select-fields/" + item.path)
			// default
			.append($("<option>")
				.attr("value", "1")  // code for any
				.text("all"))
		);

		var subset_select_field = info_div.find(".subset-select-fields");  // reference


		// info_div.append($("<label>").text())
		// info_div.append($("<select>")
		// 	.attr("class", "subset-select")
		// 	.attr("multiple", "multiple")
		// 	);

		// var subset_select = info_div.find(".subset-select");

		// Request HDF5 meta data and populate selection form
		$.ajax({
			type: "GET",
			url: "/emmapt/api/h5meta/" + item.path,
			success: function(meta_data) {
				// Create HDF5 selection form

				// Column field names of HDF5 column meta data
				for (var i in meta_data.col_fields) {
					// select
					entry = meta_data.col_fields[i];
					match_selection_box.append($("<option>")
						.attr("value", entry)
						.text(entry)
					);

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
					var subset_select = info_div.find(".subset-select");
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
							.attr("name", "subset-select/" + item.path)
						);
					subset_select = info_div.find(".subset-select");  // WARNING: only assigned locally?


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

	} else {
		// default
		info_div.html(item);
	}
}

// Trims Javascript tree excluding elements with specified type.
function trimTree(tree, exclude_type) {
	// Clone all fields except children of original tree
	// var trim_tree = {children: []};
	var trim_tree = {};
	for (var field in tree) {
		if (field != "children") {
			trim_tree[field] = tree[field];
		}
	}
	trim_tree["children"] = [];

	// loop over children
	for (var i = 0; i < tree.children.length; i++) {
		if (tree.children[i].type !== exclude_type) {
			trim_tree.children.push(
				trimTree(tree.children[i], exclude_type));
		}
	}
	return trim_tree;
}

// Recursively searches tree for regular expression matches in either keys or values
// returning true if found and false if not found.
function searchTree(elem, reg_exp) {

	// Base case
	if (typeof elem === "string") {
		// Check match for regular expression
		if (elem.match(reg_exp) !== null) {
			return true;
		}
	} else if (typeof elem === "object") {
		// includes both arrays [] and objects {}
		// also includes Null!
		for (var index in elem) {
			if (searchTree(elem[index], reg_exp)) {
				return true;
			}
		}
	}
	return false;
}

// Test if entry satisfies the minimal formatting requirement for project tree.
function validProjectTree(tree) {
	// Each project entry must have a meta.json file.
	if (!("meta" in tree)) {
		return false;
	}

	return true;  // all tests passed
}
// test_tree = {
//     name: "root",
//     type: "dir",
//     children: [
//         {
//             name: "child1",
//             type: "file",
//             children: []
//         }, 
//         {
//             name: "subfolder",
//             type: "dir",
//             children: [{name: "grandchild1", type: "file", children: []}]
//         }
//     ]
// }
// trim_tree = trimLeaves(test_tree, "file");
