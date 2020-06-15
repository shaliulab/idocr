#' Load data in ROI tables into a single tibble
#'
#' @importFrom gtools mixedsort
#' @importFrom purrr imap map discard
#' @importFrom tibble as_tibble
#' @return tibble
#' @export
load_rois <- function(experiment_folder) {
  
  R_types <- NULL
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
    as_tibble
  
  roi_data <- roi_data[
    roi_data %>%
    select(region_id, t) %>%
    duplicated %>%
    !.,
  ]
  
  if(nrow(roi_data) < 10) {
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
