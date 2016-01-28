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
			// Unselect everything except the node clicked
			var self = this;  // the node clicked, JS reference
			svg_group.selectAll("g.node")
				.filter(function(x) {return self != this;})
				.classed("selected", false);

			// Toogle clicked class for selected node
			var this_node = d3.select(this);  // shortcut, D3 reference
			this_node.classed("selected", !this_node.classed("selected"));
			// info_div.append($("<select>"))

			// Update the info bar based on the node class selection.
			// updateInfo(svg, info_div, default_meta);

			// Update info <div>
			if (this_node.classed("selected")) {
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

		// Hidden selection element for the submit form specifying the H5 file path
		// Default matrix selection to 'data'. Can be overwritten by setup form.
		info_div.append($("<select>")
			.attr("class", "hidden")
			.attr("name", "matrix-select/" + item.path)
			.append($("<option>")
				.attr("value", "data")));
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
