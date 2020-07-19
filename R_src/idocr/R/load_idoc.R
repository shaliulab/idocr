#' Load the data of an IDOC experiment
#' @importFrom data.table fread
#' @importFrom purrr map imap
#' @importFrom dplyr mutate
load_idoc <- function(experiment_folder) {

 csv_files <- list.files(path = experiment_folder, pattern = ".csv")
 controller_data <- load_controller(experiment_folder)
 roi_data <- load_rois(experiment_folder)
 
}


