#' Module to infer names of .csv files based on metadata+key or experiment_folder+key

#' Build a filename based on the metadata and a key
#' @eval document_result_folder()
#' @param metadata data.table with all information about the experiment
#' i.e. when it was done, etc
#' @param key Name of a table in the resulting database
#' @eval document_suffix()
#' @param extension Extension of file (.csv, ...)
#' @return Filename with systematic metainformation and key to differentiate
#' it from other files from the same experiment
build_filename <- function(result_folder, metadata, key=NULL, suffix="", extension=".csv") {
  
  stopifnot(!is.null(key))
  output_csv <- file.path(
    result_folder,
    paste0(
      metadata[metadata$field == 'date_time', "value"],
      "_",
      metadata[metadata$field == 'machine_id', "value"],
      "_",
      key,
      ifelse(suffix == "", suffix, paste0("_", suffix)),
      extension
    )
  )
  return(output_csv)
}

#' Find a file with matching key in a experiment_folder
#' @param experiment_folder Path to a folder with IDOC results
#' @param key String matching a file key (VAR_MAP, METADATA, ROI_1, ...)
#' @return character
find_file <- function(experiment_folder, key) {
  csv_files <- list.files(path = experiment_folder, pattern = ".csv", full.names = TRUE)
  file <- grep(pattern = key, x = csv_files, value = T)
  return(file)
}
