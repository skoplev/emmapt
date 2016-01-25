#!/usr/bin/env Rscript

# Matches TCPA cell line proteomic data to CCLE mRNA expression data.

library(bdmerge)

# DEBUG
rm(list=ls())
setwd("/Users/sk/Google Drive/projects/bdmerge/dtree/d5/s2")

db_path_CCLE = "/Users/sk/Data/CCLE expression"

# Match cell lines to CCLE data
# ------------------------------------------------

# Load CCLE meta data
ccle_info = read.table(paste0(db_path_CCLE, "/CCLE_sample_info_file_2012-10-18.txt"), sep="\t", header=TRUE)


# Match stemmed cell line descriptions.

# Remove NA's where cell lines where not found.
# ccle_ids = ccle_ids[!is.na(ccle_ids)]

# Load TCPA RPPA data for reference. Note that the original s1 data entry is overwritten with the matched CCLE cell line names.
d = readData("../s1")

# Partial matching of ccle names to TCPA names (which are long and have weird endings)
# matches from beginning.
ccle_tcpa_cell_map = charmatch(stemString(ccle_info$Cell.line.primary.name), stemString(d$meta_col$Sample.description))

# Get ids for TCPA and CCLE for the matching cell lines
# zero corresponds to ambigous results and are here excluded.
match_tcpa_id = ccle_tcpa_cell_map[!is.na(ccle_tcpa_cell_map) & ccle_tcpa_cell_map != 0]
match_ccle_id = which(!is.na(ccle_tcpa_cell_map) & ccle_tcpa_cell_map != 0)

# Annotate TCPA data with the exact matching cell line strings.
d$meta_col$cell_line_match = NA
d$meta_col$cell_line_match[match_tcpa_id] = as.character(ccle_info$Cell.line.primary.name[match_ccle_id])

writeData(d, "../s1")  # overwrites data with the matching cell line 


# Load CCLE gene expression data. From local copy of CCLE gene expression data.
ccle_mrna = readGct(paste0(db_path_CCLE, "/CCLE_Expression_Entrez_2012-09-29.gct"))

# Finding matching gene expression data based on CCLE.name, which is the unique identifier for CCLE samples.
id = match(ccle_info$CCLE.name[match_ccle_id], ccle_mrna$meta_col[,1])

# Subset of matching CCLE mRNA data.
ccle_mrna_sub = colSubset(ccle_mrna, id[!is.na(id)])  # non na entries

# Add CCLE matching cell line
ccle_mrna_sub$meta_col$cell_line_match = as.character(ccle_info$Cell.line.primary.name[match_ccle_id[!is.na(id)]])

# Writing matching CCLE data to folder
writeData(ccle_mrna_sub, target_dir=".")
