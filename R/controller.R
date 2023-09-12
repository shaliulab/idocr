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
#' @eval document_controller_data()
#' @eval document_delay()
#' @import data.table
#' @export
preprocess_controller <- function(controller_data, delay = 0) {
  
  . <- t <- NULL
  
  keep_cols <- controller_data %>% apply(., 2, function(x) !all(is.na(x)))
  controller_data <- controller_data[, keep_cols, with=F]
  
  
  controller_data <- pad_t0(controller_data)
  
  # delay the onset of the stimulus
  controller_data[, t := t + delay]
  return(controller_data)
}

validate_controller_file <- function(controller_path) {
  validate_number_of_fields(controller_path)  
  return(0)
}

#' Load a CONTROLLER_EVENTS .csv table into R
#' 
#' @importFrom data.table fread
#' @param experiment_folder Path to a folder with IDOC results
#' @export
load_controller <- function(experiment_folder) {
  
  csv_files <- list.files(path = experiment_folder, pattern = ".csv")
  controller_filename <- grep(pattern = "CONTROLLER_EVENTS", x = csv_files, value = T)
  controller_path <- file.path(experiment_folder, controller_filename)
  validate_controller_file(controller_path)
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
#' @param rectangle_data A dataframe where every row represetns a corner of a polygon
#' The position along the time axis where the polygon should be rendered should be contained
#' in a `t_ms` column. Corners belonging to the same polygon should have a unique value under `group`.
#' @export
reshape_controller <- function(rectangle_data) {
  
  stimulus <- group <- t_ms <- side <- NULL
  
  stopifnot("t_ms" %in% colnames(rectangle_data))
  stopifnot("group" %in% colnames(rectangle_data))
  
  
  event_data <- rectangle_data %>% dplyr::group_by(stimulus, group) %>%
    dplyr::summarise(t_start = min(t_ms), t_end = max(t_ms), side = unique(side)) %>%
    dplyr::mutate(idx = group) %>% dplyr::select(-group)
  
  event_data$treatment <- unlist(lapply(event_data$stimulus, remove_side))
  return(event_data)
}


#' Obtain a tidy data frame of events from a loaded dataset
#' @eval document_dataset()
#' @return data.frame where every row registers the activation of an IDOC stimulus
get_event_data <- function(dataset) {
  
  . <- NULL
  
  # one row per corner
  rectangle_data <- define_rectangle_all(dataset)
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
  
  . <- NULL
  
  controller_data <- controller_data[!duplicated(controller_data$t),]
  controller_summary <-  dplyr::full_join(index, controller_data, by = "t") %>%
    dplyr::arrange(t)
  
  first_non_nan_row <- min(which(!apply(
    is.na(controller_summary[, -1]),
    1,
    all
    )))
  
  controller_summary <- controller_summary[first_non_nan_row:nrow(controller_summary), ]


  
  # carry forward the last observation
  controller_summary <- controller_summary %>%
    apply(
      X = .,
      MARGIN = 2,
      FUN = zoo::na.locf
    )  %>%
    tibble::as_tibble(.)  
}

