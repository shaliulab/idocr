#' Load data in ROI tables into a single tibble
#'
#' @importFrom gtools mixedsort
#' @importFrom purrr imap map discard
#' @importFrom tibble as_tibble
#' @return tibble
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
  
  
  # TODO DO I have to add missing rois?
  
  roi_data$id <- paste0(run_id, "|", roi_data$region_id)
  roi_data$x <- roi_data$x - (max(roi_data$x) - min(roi_data$x)) / 2
  
  return(roi_data)
}
