#' Load the CONTROLLER_EVENTS table into R
#' 
#' @importFrom data.table fread
load_controller <- function(experiment_folder) {
  
  csv_files <- list.files(path = experiment_folder, pattern = ".csv")
  controller_filename <- grep(pattern = "CONTROLLER_EVENTS", x = csv_files, value = T)
  controller_path <- file.path(experiment_folder, controller_filename)
  controller <- data.table::fread(file = controller_path, header = T)[, -1]
  # controller <- process_controller(controller)
  
  return(controller)
}
