#' Make sure the timeseries starts at 0 and
#' all dependent variables are also set to 0
#' @param data A timeseries data.table with a column named t
#' representing time in a numeric format and assuming t starts at exactly 0
pad_t0 <- function(data) {
  if(data[1, t] != 0) {
    first_row <- copy(data[1,]) * 0
    data <- rbind(first_row, data)
  }
  return(data)
}


#' Preprocess controller
#' * Make sure the status at time 0 is present
#' * Shift all the events to account for some delay in the arrival of the stimuli
#' if the user passes a delay
#' @import data.table
#' @export
preprocess_controller <- function(controller_data, delay = 0) {
  controller_data <- pad_t0(controller_data)
  
  # delay the onset of the stimulus
  controller_data[, t := t + delay]
  return(controller_data)
}

#' Load a CONTROLLER_EVENTS .csv table into R
#' 
#' @importFrom data.table fread
#' @param experiment_folder Path to a folder with IDOC results
#' @param delay Shift this amount of seconds the onset of the stimuli forward in time
#' to account for delays in the arrival of the stimuli (stimuli delivery is not immediate)
#' @export
load_controller <- function(experiment_folder, ...) {
  
  csv_files <- list.files(path = experiment_folder, pattern = ".csv")
  controller_filename <- grep(pattern = "CONTROLLER_EVENTS", x = csv_files, value = T)
  controller_path <- file.path(experiment_folder, controller_filename)
  controller_data <- data.table::fread(file = controller_path, header = T)[, -1]
  return(controller_data)
}



get_event_data <- function(dataset) {
  # one row per corner
  rectangle_data <- define_rectangles(dataset)
  # one row per event
  event_data <- lapply(rectangle_data, reshape_controller) %>% do.call(rbind, .)
  return(event_data)
}

# get_unsigned_hardware <- function(hardware) {
#   
#   unsigned_hardware <- sapply(
#     hardware, function(x) strsplit(x, split = "_") %>%
#       sapply(., function(y) paste0(y[1], "_", y[2]))) %>% 
#     unique
#   
#   stopifnot(length(treatments[unsigned_hardware]) == length(unsigned_hardware))
#   names(unsigned_hardware) <- treatments[unsigned_hardware]
#   return(unsigned_hardware)
#   
# }
