#' Load the CONTROLLER_EVENTS table into R
#' 
#' @importFrom data.table fread
#' @export
load_controller <- function(experiment_folder, set_t0 = TRUE, delay = 0) {
  
  
  
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
  
  # delay the onset of the 
  controller_data[, t := t + delay]
  
  # rename(controller_data, "hardware", "hardware_")
  
  return(controller_data)
}


process_controller <- function(controller_data, hardware) {
  
  ## Reformat the wide table
  ### We get one row for every corner of the rectangles shown on the plot
  ### to represent when the hardware items listed in `hardware`
  ### are on
  ### The row states:
  ### * x -> the position (-1,0,1) of the corner
  ### * side -> the side where the rectangle is (-1 if on the left and 1 if on the right)
  ### * hardware -> name of the hardware item
  ### * t_ms -> time in milliseconds
  
  controller_data <- purrr::map(
    hardware,
    ~prepare_shape_data(
      controller_data = controller_data,
      hardware = .
    )
  ) %>%
    do.call(rbind, .) %>%
    dplyr::mutate(t_ms = t * 1000)
  
  
  controller_data$hardware_small <- unlist(lapply(
    strsplit(controller_data$hardware_, split = "_"),
    function(x) {
      paste(x[1:2], collapse = "_")
    }))
  
  return(controller_data)
}