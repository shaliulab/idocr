#' Load the CONTROLLER_EVENTS table into R
#' 
#' @importFrom data.table fread
load_controller <- function(experiment_folder, set_t0 = TRUE) {
  
  csv_files <- list.files(path = experiment_folder, pattern = ".csv")
  controller_filename <- grep(pattern = "CONTROLLER_EVENTS", x = csv_files, value = T)
  controller_path <- file.path(experiment_folder, controller_filename)
  controller_data <- data.table::fread(file = controller_path, header = T)[, -1]
  
  if(controller_data[1, t] != 0 & set_t0) {
    # add a row 0 for t0 where the hardware is off
    # required for the diff operation to detect a change
    # if the hardware appears on already on the first row
    # otherwise, it has no effect
    first_row <- copy(controller_data[1,]) * 0
    controller_data <- rbind(first_row, controller_data)
  }
  return(controller_data)
}
