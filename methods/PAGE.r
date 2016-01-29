#!/usr/bin/env Rscript

# WARNING, this is currently a place holder script, which merely copies the input file

print("PAGE.r executed")

library(bdmerge)
library(getopt)
library(rjson)

quantile_filter = 0.5  # combined signal strenght quantile fitler
# quantile_filter = 0.75  # combined signal strenght quantile fitler

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

config = fromJSON(file=opt$config)

input_path = names(config$input)[1]

d = readData(file_path=input_path)

writeData(d, target_dir=opt$output, base_name="data")
