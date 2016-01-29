#!/usr/bin/env Rscript

# Cross correlation benchmark.

library(bdmerge)
library(getopt)
library(rjson)

# quantile_filter = 0.5  # combined signal strenght quantile fitler
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

# # DEBUG
# rm(list=ls())
# setwd("/Users/sk/Google Drive/projects/bdmerge/bdmergepy")
# opt = list()
# opt$config = "benchmarks/KQSAU43HSS8JRXDN9MRC6IID8NCSDVXRUIV8MBO8PMV5JVLFGF/config.json"
# opt$output = "benchmarks/KQSAU43HSS8JRXDN9MRC6IID8NCSDVXRUIV8MBO8PMV5JVLFGF"
# quantile_filter = 0.5  # combined signal strenght quantile fitler


# Read config.json file
config = fromJSON(file=opt$config)

# Get quantile filter from config
quantile_filter = as.numeric(config$options$quantile_filter) / 100.0

# find two input with the most selected information
most_information_input_index = order(sapply(config$input, length), decreasing=TRUE)[1:2]
config$input = config$input[most_information_input_index]

# Get match-select values from all file entries
match_conditions = lapply(config$input, function(x) {
		return(x["match-select"])  # returns NULL if not available
})

# Force match conditions to be vectors
for (i in 1:length(match_conditions)) {
	match_conditions[[i]] = unlist(match_conditions[[i]])
}

# Get matrix-select values from all files
matrix_selections = lapply(config$input, function(x) {
	return(x["matrix-select"])
})
matrix_selections = unlist(matrix_selections)

data_file_paths = names(config$input)

# Load data specified by config file
dlists = list()
for (i in 1:length(data_file_paths)) {
	path = data_file_paths[[i]]
	dlists[[i]] = readData(file_path=path)
}

# Match data according to the provided matching conditions
dcomb = mergeDataListsByCol(
	dlists=dlists,
	match_conditions=match_conditions,
	matrix_selections=matrix_selections
	)

# dcomb[[1]]$meta_col
# dcomb[[2]]$meta_col

# image(dlists[[1]]$data)
# image(dcomb[[1]]$data)

# dim(dlists[[1]]$data)
# dim(dcomb[[1]]$data)

# dim(dlists[[2]]$data)
# dim(dcomb[[2]]$data)

# image(dcomb[[1]]$data)
# image(as.matrix(dcomb[[1]]$data))

# Remove entries that were not matched
allmissing = allMissingValuesCol(dlists=dcomb, entries=matrix_selections)  # assumes that the data name is the same
exclude = do.call('|', allmissing)

# exclude[min_columns:length(exclude)] = TRUE
if (any(exclude)) {
	dcomb = colSubsetMatchedCollection(dcomb, !exclude)
}

# min_columns = min(ncol(dlists[[1]][[matrix_selections[1]]]), ncol(dlists[[2]][[matrix_selections[2]]]))


# Replace missing values with zeros
for (i in 1:length(dcomb)) {
	x = dcomb[[i]][[matrix_selections[i]]]
	dcomb[[i]][[matrix_selections[i]]][is.na(x)] = 0.0
}


# Norm filter measuring the signal strength
# It is assumed that the signals are comparable in magnitude.
norms = list()
for (i in 1:length(dcomb)) {
	norms[[i]] = apply(dcomb[[i]][[matrix_selections[i]]], 2, function(col) {
		return(sqrt(sum(col^2)) / length(col))  # 2-norm
	})
}

summed_norm = norms[[1]] + norms[[2]]  # combined signal strength

# Filter according to combined signal strength
dcomb = colSubsetMatchedCollection(dcomb, summed_norm >= quantile(summed_norm, quantile_filter))


# Calculate sample correlations
sample_cor1 = list()
sample_cor1$meta_row = dcomb[[1]]$meta_col
sample_cor1$meta_col = dcomb[[1]]$meta_col
sample_cor2 = list()
sample_cor2$meta_row = dcomb[[2]]$meta_col
sample_cor2$meta_col = dcomb[[2]]$meta_col

sample_cor1$cmat = cor(dcomb[[1]][[matrix_selections[1]]], use="pairwise.complete.obs", method="pearson")
sample_cor2$cmat = cor(dcomb[[2]][[matrix_selections[2]]], use="pairwise.complete.obs", method="pearson")

results = list()
results$lower_tri = data.frame(
	cor1=sample_cor1$cmat[lower.tri(sample_cor1$cmat)],
	cor2=sample_cor2$cmat[lower.tri(sample_cor2$cmat)]
)

# Calculate correlation
results$cor = cor(sample_cor1$cmat[lower.tri(sample_cor1$cmat)], sample_cor2$cmat[lower.tri(sample_cor2$cmat)], use="pairwise.complete.obs")

# Linear fit
lin_fit = lm(sample_cor1$cmat[lower.tri(sample_cor1$cmat)] ~ sample_cor2$cmat[lower.tri(sample_cor2$cmat)], na.action=na.exclude)

results$r2 = summary(lin_fit)$r.squared  # r squared

# results$cor1 = sample_cor1$cmat[lower.tri(sample_cor1$cmat)]
# results$cor2 = sample_cor1$cmat[lower.tri(sample_cor1$cmat)]

# cor(sample_cor1$cmat[lower.tri(sample_cor1$cmat)], sample_cor2$cmat[lower.tri(sample_cor2$cmat)])
# plot(sample_cor1$cmat[lower.tri(sample_cor1$cmat)], sample_cor2$cmat[lower.tri(sample_cor2$cmat)])

# Write results matrix
writeData(sample_cor1, target_dir=opt$output, base_name="sampleCor1")
writeData(sample_cor2, target_dir=opt$output, base_name="sampleCor2")
writeData(results, target_dir=opt$output, base_name="results")

