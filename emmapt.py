#!/usr/bin/env python

# for production use (specifies __debug__ = False):
#!/usr/bin/env python -O

# Default at http://localhost:5000/emmapt

# Dynamic page generation of data folder structure

from flask import Flask, render_template, jsonify, send_file, after_this_request, request
from pprint import pprint
import json

import os
import sys
import inspect
import traceback
import collections  # for ordered dictionary, json loads
import zipfile
import random
import string
import shutil
import h5py  # for opening HDF5 files
import jsonpickle  # json serializer
import numpy as np
import subprocess

def zipdir(path, ziph):
	# ziph is zipfile handle
	for root, dirs, files in os.walk(path):
		for file in files:
			ziph.write(os.path.join(root, file))

def randString(n):
	return ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(n))


def debug(elem, ntrace=1):
	"""Debug print function. Prints traceback to std.err. 
	Only prints of global variable DEBUG is set to True.

	Args:
		elem: element to be evaluated
		ntrace: traceback length

	Print format: 

		Debug trace
			file name, line number, function,
				debug(var) = 
		pprint evaluation.

	Author: 
		Simon Koplev(skoplev@gmail.com)
	"""

	if __debug__:
		# Get execution frame
		frame = inspect.currentframe()

		# Get n most recent tracebacks from where debug function was called
		stack_trace = traceback.format_list(traceback.extract_stack(frame, ntrace + 1))
		stack_trace_recent = stack_trace[:-1]  # exclude last element

		# Remove last new line; replaced by = and the evaluation of the elem.
		stack_trace_string = ''.join(stack_trace_recent).rstrip('\n')

		sys.stderr.write("\nDebug trace\n" + stack_trace_string + " =\n")  # where log was called
		pprint(elem, sys.stderr)


def makeTree(node_path):
	"""Recursively generates file tree from root. Traverses file structure depth-first.

	Arguments:
		node_path: path of current subnode

	Returns: A file tree dictionary
		"name": file/folder name
		"path": full path,
		"meta": dictionary of meta data associated with node. Read fron meta.json file in the associated folder.
		"children": [] list of contained files and folders

	Author:
		Simon Koplev(skoplev@gmail.com)
	"""

	assert isinstance(node_path, basestring)  # basestring class includes both unicode and string
	node_path = node_path.rstrip("/")  # enforce paths not ending with '/'

	# Initialize subtree with root in current node
	tree = {'name': os.path.basename(node_path), 
		'path': node_path, 
		'size': os.path.getsize(node_path),
		'children': []}

	if os.path.isdir(node_path):
		tree['type'] = 'dir'
	elif os.path.isfile(node_path):
		# Test for file types
		extension = os.path.splitext(node_path)[1]
		# print extension
		if (extension == ".h5") | (extension == ".hdf5"):
			tree['type'] = "hdf5"
		else:
			tree['type'] = 'file'
	else:
		tree['type'] = "none"

	# List node directory
	if os.path.isdir(node_path):
		node_directory = os.listdir(node_path)

		for item in node_directory:
			# get item path
			item_path = node_path + "/" + item

			# Check for item type
			if item[0] == '.':  # hidden file, exclude
				continue
			if item == "meta.json":  # meta file for current node
				with open(item_path) as json_file:
					try:
						tree['meta'] = json.load(json_file)
						# Load json file into ordered dict
						# tree['meta'] = json.load(json_file, object_pairs_hook=collections.OrderedDict)
					except ValueError:
						print "Decoding JSON failed: ", item_path

			# add subtree to current node's children
			tree['children'].append(makeTree(item_path))

	return tree

app = Flask(__name__, static_url_path='/emmapt/static', static_folder='static')
app.debug = __debug__


# INTERFACE
# -------------------------------------------------------
# Complete data tree, REST query
@app.route('/emmapt/api/getdtree')
def getdtreeRoot():
	file_tree = makeTree("dtree")
	return jsonify(file_tree)

# REST API that returns data tree as json. Grants access to file structure information
# in dtree folder.
@app.route('/emmapt/api/getdtree/<path:collection>')
def getdtree(collection):
	collection_path = 'dtree/' + collection
	file_tree = makeTree(collection_path)
	return jsonify(file_tree)

# Reads plain files and returns as text.
@app.route('/emmapt/api/readFile/<path:file_path>')
def readFile(file_path):

	try:
		with open('dtree/' + file_path) as txt_file:
			data = txt_file.read(1048576)  # at most 1MB
	except (OSError, IOError) as e:
		data = ""  # file not found

	return data

# returns file and folder structure meta data
# Reads meta.json fiels. Returns nested json object.
@app.route("/emmapt/api/meta/dtree/<path:collection>")
def getMetaData(collection):
	# Get target path
	target_path = os.path.join(app.root_path, "dtree", collection)

	data = {}
	message = ""
	if os.path.isdir(target_path):
		data["type"] = "folder"
		# message = "a folder"
		# Try reading a meta.json file in folder
		with open(os.path.join(target_path, "meta.json")) as json_file:
			try:
				data["meta"] = json.load(json_file)
				return jsonify(data)
				# Load json file into ordered dict
			except ValueError:
				print "Decoding JSON failed: ", item_path

	elif os.path.isfile(target_path):
		data["type"] = "file"
		data["path"] = collection
		data["size"] = os.path.getsize(target_path)
		return jsonify(data)
		# message = "a file"
	else:
		message = "ERROR"
	return "output from metadata api with input " + collection + ". " + message

# Reads meta data of HDF5 file and returns json object containing field names
# and lists of unique entries for each field.
@app.route("/emmapt/api/h5meta/dtree/<path:collection>")
def getH5Meta(collection):
	target_path = os.path.join(app.root_path, "dtree", collection)

	# Open HDF5 file
	f = h5py.File(target_path, "r")

	# print type(f.keys())

	meta = dict()

	# Get all entries to 
	matrix_list = f.keys()
	matrix_list.remove("meta_col")
	matrix_list.remove("meta_row")

	meta["matrices"] = matrix_list

	# Load meta data
	meta_col = f["meta_col"]  # HDF5 data set object
	meta_row = f["meta_row"]

	# Field names of column and row meta data
	meta["col_fields"] = meta_col.dtype.names
	meta["row_fields"] = meta_row.dtype.names

	# Unique values of column and row meta data
	meta["col_fields_values"] = list()

	for field in meta["col_fields"]:
		# Find unique entries
		unique_list = list(set(meta_col[field]))

		unique_list = [str(entry) for entry in unique_list]  # force string format for json encoding compatability

		meta["col_fields_values"].append(unique_list)

	return jsonify(meta)


# @app.route("/emmapt/api/h5metaColFields/dtree/<path:collection>")
# def getH5MetaColField(collection):
# 	target_path = os.path.join(app.root_path, "dtree", collection)

# 	# Open HDF5 file
# 	f = h5py.File(target_path, "r")

# 	# Load meta data
# 	meta_col = f["meta_col"]  # HDF5 data set object

# 	# print type(list(meta_col.dtype.names))
# 	# print list(meta_col.dtype.names)

# 	return jsonify(col_fields=meta_col.dtype.names)

# SITE ROUTES
# ----------------------------------------------------
@app.route('/emmapt')
def indexPage():
	return render_template('index.html', 
		title="Biological data merges")

@app.route('/emmapt/browse')
def browsePage():
	return render_template('browse.html',
		title="Download")

# Note that the download implementation currently allows one to download anything which is referenced in
# the /emmapt folder. Which would be a major security risk in production.
@app.route('/emmapt/download/dtree/<path:file_name>')
def download(file_name):
	target_path = os.path.join(app.root_path, "dtree", file_name)

	if os.path.isfile(target_path):
		# file
		return send_file(target_path)
	elif os.path.isdir(target_path):
		# Store data package in random temporary folder
		rand_dir = randString(10)
		os.mkdir(os.path.join("tmp", rand_dir))

		zipf = zipfile.ZipFile(os.path.join("tmp", rand_dir, "dataPackage.zip"), 'w')

		zipdir(os.path.join("dtree", file_name), zipf)
		zipf.close()

		@after_this_request
		def cleanUp(response):
			shutil.rmtree(os.path.join("tmp", rand_dir))
			return(response)

		return send_file(os.path.join(app.root_path, "tmp", rand_dir, "dataPackage.zip"))
	else:
		return render_template('error.html', err_msg=" entry does not exist")


@app.route('/emmapt/challenges')
def challengesPage():
	return render_template('challenges.html',
		title="Challenges")

@app.route('/emmapt/docs')
def docsPage():
	return render_template('docs.html',
		title="Documentation")

@app.route('/emmapt/about')
def aboutPage():
	return render_template('about.html',
		title='About')

@app.route('/emmapt/project_description')
def descriptionPage():
	return render_template('project_description.html', title="Project description")


# Data view for collection of data. Entries in the dtree folder.
@app.route('/emmapt/project/<path:collection>')
def projectPage(collection):
	collection_path = 'dtree/' + collection

	if not os.path.exists(collection_path):
		return render_template('error.html', err_msg=" folder does not exist")
	# path does exist

	# todo, catch not found error...
	return render_template('project.html',
		data_collection=collection,  # data collection
		title="Project: " + collection)


@app.route('/emmapt/bench', methods=["POST"])
def benchmark():
	results_code_size = 50
	# Load necesary data
	# data = request.json
	# print "post data: "
	# print data
	# print json.dumps(data)

	# print request.form["firstname"]
	# print request.form  # immutable dictionary

	# print request.args
	# print request.form  # get all post field names
	# print request.form.keys()

	# print request.form.keys()[2]
	# print request.form.keys()[2].split("/", 1)  # split by first '/'

	# Interpret POST request
	file_options = dict()  # path -> cmd -> [arguments]
	options = dict()  # general options
	# Loop over POST variable names
	for key in request.form:
		# print request.form.getlist(key)

		a = key.split("/", 1)
		if len(a) == 2:
			# POST input has both command and path
			cmd = a[0]
			path = a[1]  # unique identifier for submitted data matrices

			# init HDF5 path if not previously seen
			if not path in file_options:
				file_options[path] = dict()  # list of commands on the form (cmd, [arguments])
 
			file_options[path][cmd] = request.form.getlist(key)  # includes single arguments as 1-lists
		else:
			options[key] = request.form.getlist(key)

	pprint(file_options)
	pprint(options)

	# make random folder for output
	results_code = randString(results_code_size)
	results_path = "benchmarks/" + results_code
	os.mkdir(results_path)

	# Write config as file
	with open(results_path + "/config.json", "w") as config_file:
		json.dump(dict(input=file_options, opts=options), config_file, indent=4, sort_keys=True)

	# Call method in r
	# os.system("methods/crossCorSample.r -c " + results_path + "/config.json" + " -o " + results_path)

	# method_output = subprocess.check_output(
	# 	["methods/crossCorSample.r", "-c", results_path + "/config.json", "-o", results_path],
	# 	stderr=subprocess.PIPE
	# 	)

	# try:
	try:
		method_output = subprocess.check_output(
			["methods/crossCorSample.r", "-c", results_path + "/config.json", "-o", results_path],
			stderr=subprocess.STDOUT
			# stdout=subprocess.STDOUT,
			# shell=True
			)

	except subprocess.CalledProcessError as e:
		# Transform to RunrimeError which es handled by Flask
		raise RuntimeError("command '{}' return with error (code {}): {}".format(e.cmd, e.returncode, e.output))


	# Read files, TODO separate
	# send as data

	# Read data
	cor1 = h5py.File(results_path + "/sampleCor1.h5", "r")
	cor2 = h5py.File(results_path + "/sampleCor2.h5", "r")
	results = h5py.File(results_path + "/results.h5", "r")


	results_table = results["lower_tri"][()]  # read entire table into memory

	# print np.reshape(cor1["cmat"], 1)
	# print cor1["cmat1"].reshape
	# Lower triangle
	# print np.tril(cor1["cmat"], k=-1)

	# # Loop over correlation matrices generating the data structure for D3
	# it1 = np.nditer(cor1["cmat"], flags=["f_index"], op_dtypes=["float64"], casting=["same_kind"])
	# it2 = np.nditer(cor2["cmat"], flags=["f_index"], op_dtypes=["float64"], casting=["same_kind"])

	cross_cor_data = list()

	# # keep track of index
	# while not it1.finished:
	# 	# print it1[0], it1.index
	# 	cross_cor_data.append([it1[0], it2[0]])

	# 	it1.iternext()
	# 	it2.iternext()

	return render_template('benchmark.html', opts=json.dumps(file_options), data_set=json.dumps(results_table.tolist()))


@app.route('/emmapt/dtree/<path:file_path>')
def filePage(file_path):

	# Mapping from file extensions to language names
	languages = {
		".r": "r",
		".R": "r",
		".py": "python",
		".cpp": "cpp",
		".sh": "bash",
		".json": "json",
		".js": "javascript",
		".md": "markdown",
		".java": "java",
	}

	# data types
	dtypes = {
		".tsv": "tsv",
		".h5": "hdf5"
	}

	# check if request is a folder and redirect to project page
	if os.path.isdir("dtree/" + file_path):
		# redirect to project page
		# return "it's a folder..."
		return projectPage(file_path)


	# Guess file type
	# Get file extension, base path (path without file extension), and base name
	base_path, file_ext = os.path.splitext(file_path)
	base_name = base_path.split("/")[-1]


	# Guess the code type based on file ending
	code_class = ""
	if file_ext == "":
		# file has no . extension
		if base_name == "Makefile":
			code_class = "makefile"
	else:
		# file has . extension
		try:
			code_class = "lang-" + languages[file_ext]
		except KeyError:
			pass

	# Try to open data file
	with open("dtree/" + file_path) as txt_file:
		# data = txt_file.read(1000000)  # at most 1MB
		# data = txt_file.read(100000)  # at most 100kB
		data = txt_file.read(10000)  # at most 10kB

	# return data
	return render_template("file.html",
		file_path=file_path,
		code_class=code_class,
		title=""
		)


if __name__ == "__main__":
	# app.run(host="0.0.0.0", port=80)
	app.run(host="0.0.0.0", port=5000)
