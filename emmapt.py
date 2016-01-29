#!/usr/bin/env python

# for production use (specifies __debug__ = False):
#!/usr/bin/env python -O

# Default at http://localhost:5000/emmapt

# Dynamic page generation of data folder structure

from flask import Flask, render_template, jsonify, send_file, after_this_request, request, redirect, url_for
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
import time
import datetime

# Scheduler
from apscheduler.scheduler import Scheduler
import logging

SESSION_ID_LENGTH = 50  # code length of user session id's


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

# Interpret POST requests.
# Supports requests on the format "<command>/<path>" = [attributes]
# Extracts entire request and returns an interpreted dictionary.
def interpretPostRequest(request):
	config = dict()

	# config["method"] = ""
	if "method" in request.form:
		config["method"] = request.form["method"]

	config["input"] = dict()  # path -> cmd -> [arguments]

	config["options"] = dict()  # general options
	# Loop over POST variable names
	for key in request.form:
		command_path = key.split("/", 1)  # first '/' is used to separate command from path
		if len(command_path) == 2:
			# format is   "<command>/<path>" = [attributes]
			# POST input has both command and path
			cmd = command_path[0]
			path = command_path[1]  # unique identifier for submitted data matrices

			# init HDF5 path if not previously seen
			if not path in config["input"]:
				config["input"][path] = dict()  # list of commands on the form (cmd, [arguments])
	
			config["input"][path][cmd] = request.form.getlist(key)  # includes single arguments as 1-lists
		elif key != "method":
			config["options"][key] = request.form.getlist(key)

	return config

# Returns list of single input configs 
# Assumes that the separation of input into single commands makes sense.
# Function is used to assist the POST interface.
def separateConfigDictByInput(multi_config):

	single_configs = list()
	for h5file in multi_config["input"]:
		config = dict()  # new dict config specific to the h5path
		config["input"] = dict()

		config["input"][h5file] = multi_config["input"][h5file]
		# copy method and options to base. Introduces redundancy in the config file
		config["method"] = multi_config["input"][h5file]["method"]
		try:
			config["options"] = multi_config["input"][h5file]["options"]
		except KeyError:
			pass

		single_configs.append(config)

	return single_configs

# Flask application
# ---------------------------------
app = Flask(__name__, static_url_path='/emmapt/static', static_folder='static')
app.debug = __debug__

# Initialize scheduler
scheduler = Scheduler()
scheduler.start()  # init

logging.basicConfig()  # initializes logging, which is required for 

# Clean the ./tmp folder in seconds intervals.
# Removes folders and files that are older than the specified number of minutes
@scheduler.interval_schedule(seconds=3600*24)
def cleanTemporaryDirectories(storage_time_minutes=60*24*30):
	# Loop over entries in the temporary directory
	for name in os.listdir("./tmp"):
		path = "./tmp/" + name
		# calculate time since creation, in minutes
		ellapsed_time_minutes = (time.time() - os.path.getmtime(path)) / 60

		if ellapsed_time_minutes > storage_time_minutes:
			# remove file or folder (recursively)
			if os.path.isfile(path):
				os.remove(path)
			elif os.path.isdir(path):
				print "/tmp cleanup. too old removing folder " + path
				shutil.rmtree(path)

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
	# print "getMetaData called"
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
@app.route("/emmapt/api/h5meta/<path:collection>")
def getH5Meta(collection):
	target_path = os.path.join(app.root_path, collection)

	# Open HDF5 file
	f = h5py.File(target_path, "r")

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

	# get default selection of data entry, from root data collection meta.json file
	collection_path = collection.split("/")
	base_entry = collection_path[0] + "/" + collection_path[1]
	try:
		with open(os.path.join(app.root_path, collection_path[0], collection_path[1], "meta.json")) as json_file:
			try:
				collection_meta = json.load(json_file)
				meta["default_match"] = collection_meta["default_match"]
			except ValueError:
				print "Decoding JSON failed: ", collection_path
			except KeyError:
				pass
	except IOError:
		pass

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

# Generates new random session id's and creates local folder in /tmp/<id> folder.
# Returns the path to the created folder.
def makeLocalPath(local_id):
	local_path = "tmp/" + local_id
	os.mkdir(local_path)
	return local_path

# Configuration of pretransforms.
# This is the first instance of the setup, which creates a session id
@app.route("/emmapt/setupTransform", methods=["POST"])
def setupTransform():
	session_id = randString(SESSION_ID_LENGTH)
	local_path = makeLocalPath(session_id)
	config = interpretPostRequest(request)

	# Write general config as file to local path, may be overwritten by the transform compilation.
	with open(local_path + "/config.json", "w") as config_file:
		json.dump(config, config_file, indent=4, sort_keys=True)

	# setup_form = "setup" + os.path.splitext(config["method"])[0]

	return render_template("setupTransform.html", request_id=session_id, h5input_files=config["input"].keys(), method=config["method"])

@app.route("/emmapt/runTransform/<request_id>", methods=["POST"])
def runTransform(request_id):
	session_path = os.path.join("tmp", request_id)

	# Interpret the transformation POST request
	transform_config = interpretPostRequest(request)
	sep_transform_configs = separateConfigDictByInput(transform_config)

	# pprint(transform_config)
	# pprint(sep_transform_configs)

	# Open config from file
	# Init method configuation, which is based on the output of the transforms
	with open(session_path + "/config.json") as json_file:
		method_config = json.load(json_file)

	# Reset config specifications
	method_config["input"] = dict()
	method_config["options"] = dict()


	# Run each command and store the config.json in the apropriate tree structure.
	for config in sep_transform_configs:
		# Get the 
		h5path = config["input"].keys()[0]
		if ("method" not in config) or (config["method"][0] == "none"):
			# no transform, store original h5path provided from POST request
			method_config["input"][h5path] = dict()  # dictionary specification by convention
		else:
			# Create new local folder for transformation output
			local_out_folder = os.path.join(session_path, os.path.dirname(h5path), config["method"][0])
			os.makedirs(local_out_folder)

			# write config file to local data path. Used for input and for provenance.
			with open(local_out_folder + "/config.json", "w") as config_file:
				json.dump(config, config_file, indent=4, sort_keys=True)

			# Call transformation method 
			try:
				method_output = subprocess.check_output(
					["methods/" + config["method"][0], "-c", local_out_folder + "/config.json", "-o", local_out_folder],
					stderr=subprocess.STDOUT
					# stdout=subprocess.STDOUT,
					# shell=True
					)

			except subprocess.CalledProcessError as e:
				# Transform to RunrimeError which es handled by Flask
				raise RuntimeError("command '{}' return with error (code {}): {}".format(e.cmd, e.returncode, e.output))

			# Store the local HDF5 file path for next analysis step
			method_config["input"][local_out_folder + "/data.h5"] = dict()

	# write the config for the integrative method in base folder
	with open(session_path + "/config.json", "w") as config_file:
		json.dump(method_config, config_file, indent=4, sort_keys=True)

	# Redirect to integrative method setup
	return redirect(url_for("setupMethod", session_id=request_id))

# Configuration of method
@app.route("/emmapt/setupMethod", methods=["POST", "GET"])
def setupMethod():
	if "session_id" in request.args:
		# retrieve session id
		session_id = request.args["session_id"]
		session_path = "tmp/" + session_id

		# Load config file
		with open(session_path + "/config.json") as json_file:
			config = json.load(json_file)
	else:
		# Initiate new session, with config from POST request
		session_id = randString(SESSION_ID_LENGTH)
		local_path = makeLocalPath(session_id)
		config = interpretPostRequest(request)

		# Write config as file to 
		with open(local_path + "/config.json", "w") as config_file:
			json.dump(config, config_file, indent=4, sort_keys=True)

	setup_form = "setup" + os.path.splitext(config["method"])[0]

	return render_template(setup_form + ".html", request_id=session_id, h5input_files=config["input"].keys())


@app.route('/emmapt/runMethod/<request_id>', methods=["POST"])
def runMethod(request_id):
	# results_code_size = 50  # code length of result id's

	session_path = "tmp/" + request_id

	# Open config from file
	with open(session_path + "/config.json") as json_file:
		config = json.load(json_file)

	# Interpret POST request modifying the config file accordingly, new config items have precedence
	config = dict(config.items() + interpretPostRequest(request).items())

	# Write config as file to 
	with open(session_path + "/config.json", "w") as config_file:
		json.dump(config, config_file, indent=4, sort_keys=True)

	# Call method in r
	try:
		method_output = subprocess.check_output(
			["methods/" + config["method"], "-c", session_path + "/config.json", "-o", session_path],
			stderr=subprocess.STDOUT
			# stdout=subprocess.STDOUT,
			# shell=True
			)

	except subprocess.CalledProcessError as e:
		# Transform to RunrimeError which es handled by Flask
		raise RuntimeError("command '{}' return with error (code {}): {}".format(e.cmd, e.returncode, e.output))

	# Get the Flask visualizer function name
	visualizer = "result" + os.path.splitext(config["method"])[0]

	# Redirect to output page for specific method
	return redirect(url_for(visualizer, result_id=request_id))

# Route to the result of running a method, with particular id. 
# Data is stored on the server in the /tmp folder which
# is occasionally cleaned for old entries.
@app.route("/emmapt/resultMUTCO/<result_id>")
def resultMUTCO(result_id):
	result_path = "tmp/" + result_id

	# Load the config file
	with open(result_path + "/config.json") as json_file:
		config = json.load(json_file)

	# Read data
	cor1 = h5py.File(result_path + "/sampleCor1.h5", "r")
	cor2 = h5py.File(result_path + "/sampleCor2.h5", "r")
	results = h5py.File(result_path + "/results.h5", "r")

	results_table = results["lower_tri"][()]  # read entire table into memory

	return render_template('resultMUTCO.html', opts=json.dumps(config), data_set=json.dumps(results_table.tolist()))

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
	# app.run(host="0.0.0.0", port=5000, use_reloader=False)  # disables use_reloader, initializes only once
	app.run(host="0.0.0.0", port=5000)

