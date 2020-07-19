#' @importFrom data.table fread
#'@export
load_metadata <- function(experiment_folder) {
  
  csv_files <- list.files(path = experiment_folder, pattern = ".csv")
  metadata_filename <- grep(pattern = "METADATA", x = csv_files, value = T)
  metadata <- data.table::fread(file.path(experiment_folder, metadata_filename), header = T)
  return(metadata)
}
