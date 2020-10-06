#' @importFrom data.table fread
#' @export
load_varmap <- function(experiment_folder) {
  
  csv_files <- list.files(path = experiment_folder, pattern = ".csv")
  var_map_filename <- grep(pattern = "VAR_MAP", x = csv_files, value = T)
  var_map_path <- file.path(experiment_folder, var_map_filename)
  var_map <- data.table::fread(file = var_map_path, header = T)[, -1]
  return(var_map)
}



#' @importFrom data.table fread
#'@export
load_metadata <- function(experiment_folder) {
  
  csv_files <- list.files(path = experiment_folder, pattern = ".csv")
  metadata_filename <- grep(pattern = "METADATA", x = csv_files, value = T)
  metadata <- data.table::fread(file.path(experiment_folder, metadata_filename), header = T)
  return(metadata)
}


#' Load data in ROI tables into a single tibble
#'
#' @importFrom gtools mixedsort
#' @importFrom purrr imap map discard
#' @importFrom tibble as_tibble
#' @return tibble
#' @export
load_rois <- function(experiment_folder) {
  
  # R_types <- NULL
  csv_files <- list.files(path = experiment_folder, pattern = ".csv")
  
  metadata <- load_metadata(experiment_folder)
  run_id <- metadata[field == "run_id", value]
  
  # keep the ROI_* files only and in numerical order i.e. 10 after 9 and not after 1
  roi_files <- gtools::mixedsort(grep(pattern = "ROI_\\d", x = csv_files, value = T))
  
  roi_data <- roi_files %>%
    purrr::map(~ file.path(experiment_folder, .)) %>%
    purrr::map(~data.table::fread(.x, header = T)[, -1]) %>%
    purrr::imap(~cbind(.x, region_id = .y)) %>%
    purrr::discard(~ nrow(.x) < 10) %>%
    do.call(rbind, .) %>%
    tibble::as_tibble(.)
  
  roi_data <- roi_data[
    roi_data %>%
      select(region_id, t) %>%
      duplicated %>%
      !.,
    ]
  
  if (nrow(roi_data) < 10) {
    return(NULL)
  }
  
  roi_data$id <- paste0(run_id, "|", roi_data$region_id)
  #roi_data$x <- roi_data$x - (max(roi_data$x) - min(roi_data$x)) / 2
  
  # center the data around the median
  # i.e. estimate the center of the chamber using the median x
  # roi_data$x <- roi_data$x - median(roi_data$x)
  x <- roi_data$x - min(roi_data$x)
  x <- x - max(x) / 2
  roi_data$x <- x
  
  
  # keep only needed columns
  var_map <- load_varmap(experiment_folder)
  roi_data <- roi_data[,c(var_map$var_name, names(get_extra_columns()))]
  
  return(roi_data)
}


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


