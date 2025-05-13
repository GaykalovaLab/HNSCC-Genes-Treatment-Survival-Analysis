# Set CRAN mirror  
options(repos = c(CRAN = "https://cloud.r-project.org"))

# Install and load required packages
is_gtsummary_available <- require("gtsummary")
if (!is_gtsummary_available) {
  if (!require("BiocManager", quietly = TRUE))
    install.packages("BiocManager")
  BiocManager::install("gtsummary")
}

if (!require("cardx", quietly = TRUE)) {
  install.packages("cardx")
}

library("gtsummary")
library("cardx")
library("dplyr")  # Ensure dplyr is loaded for %>%
library("tibble") # Required to convert table to data frame

# Read command-line arguments
args = commandArgs(trailingOnly=TRUE)

if (length(args) < 1) {
  stop("Error: At least one argument (input table for cohort summary) is required.")
}

path_to_cohort_data <- args[1]
path_to_status_data <- ifelse(length(args) > 1, args[2], path_to_cohort_data)
path_to_output <- ifelse(length(args) > 2, args[3], "output")

# Ensure output path is a valid directory
if (!dir.exists(path_to_output)) {
  dir.create(path_to_output, recursive = TRUE, showWarnings = FALSE)
}

cohort_output_file <- file.path(path_to_output, "survival_summary_cohort.csv")
status_output_file <- file.path(path_to_output, "survival_summary_status.csv")

print(paste("Cohort input table path:", path_to_cohort_data))
print(paste("Status input table path:", path_to_status_data))
print(paste("Cohort summary output file:", cohort_output_file))
print(paste("Status summary output file:", status_output_file))

# Read the input CSV files
df_cohort <- read.csv(path_to_cohort_data)
df_status <- read.csv(path_to_status_data)

# Ensure required columns exist in df for cohort analysis
required_cols_cohort <- c("age", "sex", "race", "smoking", "p16", "alcohol", 
                          "cancer_type", "anatomic_stage", "lvi", "pni", "cohort")

missing_cols_cohort <- setdiff(required_cols_cohort, colnames(df_cohort))
if (length(missing_cols_cohort) > 0) {
  stop("Missing required columns for cohort analysis: ", paste(missing_cols_cohort, collapse=", "))
}

# Ensure required columns exist in df for status analysis
required_cols_status <- c("age", "sex", "race", "smoking", "alcohol", "drugs", "p16", 
                          "cancer_type", "anatomic_stage", "prior_cancer",
                          "pdl1", "pni", "ene", "lvi", "response_0", "treatment_type0", "status")

missing_cols_status <- setdiff(required_cols_status, colnames(df_status))
if (length(missing_cols_status) > 0) {
  stop("Missing required columns for status analysis: ", paste(missing_cols_status, collapse=", "))
}

# Create the summary table by cohort
table_cohort <- df_cohort %>%
  tbl_summary(
    by = "cohort",
    include = required_cols_cohort
  ) %>%
  add_p() %>% 
  add_n() %>%
  bold_labels()

# Convert cohort summary table to a data frame
table_cohort_df <- as_tibble(table_cohort)

# Save cohort summary table as CSV
write.csv(table_cohort_df, cohort_output_file, row.names = FALSE)

# Create the summary table by status
table_status <- df_status %>%
  tbl_summary(
    by = "status",
    include = required_cols_status
  ) %>%
  add_p() %>%
  add_n() %>%
  modify_header(label = "**Status: alive or passed away**") %>%
  bold_labels() %>%
  add_overall()

# Convert status summary table to a data frame
table_status_df <- as_tibble(table_status)

# Save status summary table as CSV
write.csv(table_status_df, status_output_file, row.names = FALSE)

print(paste("Cohort summary table saved to:", cohort_output_file))
print(paste("Status summary table saved to:", status_output_file))
