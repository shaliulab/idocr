#' Export a single csv with all key data for analysis and plotting outside of R
#' 
#' @importFrom tidyr pivot_wider
#' @importFrom dplyr select, mutate, arrange
#' @importFrom zoo na.locf
#' @importFrom tibble as_tibble
#' @import magrittr
export_summary <- function(experiment_folder, output_csv) {
  
  roi_data <- load_rois(experiment_folder = experiment_folder)
  controller_data <- load_controller(experiment_folder = experiment_folder, set_t0 = TRUE)
  
  roi_summary <- roi_data %>%
    select(t, x, region_id) %>%
    mutate(region_id = paste0("ROI_", region_id)) %>%
    tidyr::pivot_wider(data = ., values_from = x, names_from = region_id)
  
  # TODO Export var map of controller data in Python
  # for now just deselecting elapsed_seconds
  # This is fragile. If a new column is added to the
  # CONTROLLER_EVENTS table, this code could a bug
  
  # Extend the controller data by adding one row for each frame that was analyzed
  controller_summary <- controller_data %>% select(-elapsed_seconds) %>%
    dplyr::full_join(roi_summary[, "t"], ., on = "t") %>%
    arrange(t)
  
  controller_summary <- controller_summary %>%
    apply(
      X = .,
      MARGIN = 2,
      FUN = na.locf
    ) %>%
    as_tibble
  
  summary_data <- dplyr::full_join(roi_summary, controller_summary, on = "t")
  fwrite(x = summary_data, file = output_csv, sep = ",", col.names = TRUE)
}
  