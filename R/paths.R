#' Module to infer names of .csv files based on metadata+key or experiment_folder+key

#' Build a filename based on the metadata and a key
#' @param metadata data.table with all information about the experiment
#' i.e. when it was done, etc
#' @param key Name of a table in the resulting database
#' @param extension Extension of file (.csv, ...)
#' @return Filename with systematic metainformation and key to differentiate
#' it from other files from the same experiment
build_filename <- function(experiment_folder=NULL, metadata=NULL, key=NULL, extension=".csv") {
  
  if (is.null(experiment_folder) & !is.null(metadata))
    experiment_folder <- "."
  else if (!is.null(experiment_folder) & is.null(metadata))
    metadata <- load_metadata(experiment_folder)
  else if(!is.null(experiment_folder) & !is.null(metadata)) {
  }
  else
    stop("Please pass at least experiment_folder or metadata")
  
  stopifnot(!is.null(key))
  
  output_csv <- file.path(
    experiment_folder,
    paste0(metadata[metadata$field == 'date_time', "value"],
           "_",
           metadata[metadata$field == 'machine_id', "value"],
           "_",
           key,
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
