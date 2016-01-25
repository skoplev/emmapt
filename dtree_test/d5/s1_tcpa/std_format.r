#!/usr/bin/env Rscript

# TCPA data downloaded from
# http://app1.bioinformatics.mdanderson.org/tcpa/_design/basic/download.html
# Catagory "MDACC"

library(bdmerge)

# DEBUG
rm(list=ls())
setwd("/Users/sk/Google Drive/projects/bdmerge/dtree/d5/s1")

parseTCPAmat = function(mat, meta_cols) {
	gene_names = colnames(mat)[(meta_cols+1):ncol(mat)]

	out = list()
	out$meta_row = data.frame(TCPA_protein_marker_id=gene_names)
	out$meta_col = mat[,1:meta_cols]
	out$data= t(mat[,(meta_cols+1):ncol(mat)])

	return(out)
}

# Load data
unzip("data.zip", exdir="tmp")

d35 = read.table("tmp/data/MDACC-CELLLINE_S35-L3-S35.csv", header=TRUE, sep=",")
d40 = read.table("tmp/data/MDACC-CELLLINE_S40-L3-S40.csv", header=TRUE, sep=",")
d51 = read.table("tmp/data/MDACC-CELLLINE_S51-L3-S51.csv", header=TRUE, sep=",")

# Format data
# d29_form = parseTCPAmat(d29, 8)
d35_form = parseTCPAmat(d35, 4)
d40_form = parseTCPAmat(d40, 4)
d51_form = parseTCPAmat(d51, 4)

# combine in single data structure
dcomb = mergeDataListsByRow(d35_form, d40_form, row_id="TCPA_protein_marker_id")
dcomb = mergeDataListsByRow(dcomb, d51_form, row_id="TCPA_protein_marker_id")

# Write as HDF5 file
writeData(dcomb)

unlink("tmp", recursive=TRUE)
