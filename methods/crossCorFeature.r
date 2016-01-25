#!/usr/bin/env Rscript

# Cross correlation benchmark.

library(bdmerge)
library(getopt)
library(rjson)

opt = getopt(c(
		"config", "c", 1, "character", # config file path
		"output", "o", 1, "character" # output folder
	))

if (is.null(opt$config)) {
	stop("No config file provided")
}

if (is.null(opt$output)) {
	stop("No output folder specified")
}

# # DEBUG
# rm(list=ls())
# setwd("/Users/sk/Google Drive/projects/bdmerge/bdmergepy")
# opt = list()
# opt$config = "benchmarks/TWWXO3VHT3Y0S18FJTK5HJO2UBQEMMD00NQ9W9FEDLVFRDAXCN/config.json"
# opt$output = "benchmarks/TWWXO3VHT3Y0S18FJTK5HJO2UBQEMMD00NQ9W9FEDLVFRDAXCN"

# Read config.json file
config = fromJSON(file=opt$config)

# Get match-select values from all file entries
match_conditions = lapply(config$input, function(x) {
		return(x["match-select"])
	}
)

data_file_paths = names(config$input)

# Load data specified by config file
dlists = list()
for (i in 1:length(data_file_paths)) {
	path = data_file_paths[[i]]
	dlists[[i]] = readData(file_path=path)
}

# Match data according to the provided matching conditions
d = mergeDataListsByCol(dlists, match_conditions)

# Calculate Pearson's cross-correlation of first two matched entries
out = list()
out$cmat = cor(t(d[[1]]$data), t(d[[2]]$data), use="pairwise.complete.obs", method="pearson")
out$meta_row = d[[1]]$meta_row
out$meta_col = d[[2]]$meta_row

# Write results matrix
writeData(out, opt$output)

