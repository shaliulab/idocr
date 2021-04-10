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
#' @eval document_delay()
#' @export
load_controller <- function(experiment_folder, ...) {
  
  csv_files <- list.files(path = experiment_folder, pattern = ".csv")
  controller_filename <- grep(pattern = "CONTROLLER_EVENTS", x = csv_files, value = T)
  controller_path <- file.path(experiment_folder, controller_filename)
  controller_data <- data.table::fread(file = controller_path, header = T)[, -1]
  return(controller_data)
}

#' Reshape controller data to a format where it is
#' easy to merge with cross_data
#' 
#' Enter a dataframe with one row per corner
#' get a new dataframe with one row per event (1/4 of the rows)
#' @importFrom magrittr `%>%` 
#' @importFrom dplyr group_by summarise select mutate
#' @export
reshape_controller <- function(rectangle_data) {
  
  event_data <- rectangle_data %>% dplyr::group_by(stimulus, group) %>%
    dplyr::summarise(t_start = min(t_ms), t_end = max(t_ms), side = unique(side)) %>%
    dplyr::mutate(idx = group) %>% dplyr::select(-group)
  
  event_data$treatment <- unlist(lapply(
    event_data$stimulus, function(x) {
      treatm <- gsub(pattern = "_LEFT", replacement = "", x = x)
      treatm <- gsub(pattern = "_RIGHT", replacement = "", x = treatm)
    }))
  return(event_data)
}


#' TODO
#' @param controller_data
#' @return event_data
get_event_data <- function(dataset) {
  
  . <- NULL
  
  # one row per corner
  rectangle_data <- define_rectangles(dataset)
  # one row per event
  event_data <- lapply(rectangle_data, reshape_controller) %>% do.call(rbind, .)
  return(event_data)
}


#' Interpolate controller recordings
#' Interpolate the recordings registered in the controller data
#' by adding new interpolated ones, one for each new timepoint in index
#' The interpolation is done by carrying forward the last observation
#' @importFrom dplyr arrange full_join
#' @importFrom zoo na.locf
#' @importFrom tibble as_tibble
#' @importFrom magrittr `%>%`
#' @eval document_controller_data()
#' @param index data.frame with a column named t containing timepoints
#' not available in controller_data (but contained within its min-max interval) 
interpolate_controller <- function(controller_data, index) {
  
  controller_summary <- controller_data %>%
    dplyr::full_join(index, ., on = "t") %>%
    dplyr::arrange(t)
  
  # carry forward the last observation
  controller_summary <- controller_summary %>%
    apply(
      X = .,
      MARGIN = 2,
      FUN = zoo::na.locf
    ) %>%
    tibble::as_tibble(.)    
}

