#' The standard idocr workflow.
#' 
#' Load data from the experiment folder, possibly with some specific settings
#' and return a data frame with the apetitive index of each fly
#' and a plot visualizing the experiment
#' @importFrom dplyr nest_by summarise group_by
#' @import ggplot2
#' @importFrom purrr map
#' @importFrom data.table fwrite
#' @export
idocr <- function(experiment_folder, hardware = c("TREATMENT_A_LEFT",  "TREATMENT_A_RIGHT", "TREATMENT_B_LEFT",  "TREATMENT_B_RIGHT"),
                  border_mm = 5, min_exits_required = 5, CSplus="TREATMENT_A", delay = 0,
                  src_file = NULL,
                  ...) {
  
  
  document_script(src_file, experiment_folder)


  # Convert human understandable mm
  # to pixels that are easy to work with in R
  pixel_to_mm_ratio <- 2.3
  border <- border_mm * pixel_to_mm_ratio
  plot_decision_zone <- TRUE
  
  
  # Load tracking data (ROI - Region of Interest)
  roi_data <- load_rois(experiment_folder)
  roi_data <- add_empty_roi(experiment_folder, roi_data, n=20)
  
  

  # Load controller data
  ## Wide format table where every piece of hardware ahs a column and the values are 1 or 0
  ## An extra column called t tells the time in seconds
  controller_data <- load_controller(experiment_folder, delay=delay)
  
  ##
  controller_data <- process_controller(controller_data, hardware)
  cross_data <- infer_decision_zone_exits(roi_data, border=border)
  event_data <- get_event_data(controller_data)
  
  unique_hardware <- unique(controller_data$hardware_small)
  CSminus <- unique_hardware[unique_hardware != CSplus]
  
  
  preference_data <- compute_preference_data(cross_data, event_data, CSplus, CSminus)

  # Compute the preference index based on region-id indexed data
 
  pi_data <- preference_data %>%
    dplyr::group_by(region_id, type) %>%
    dplyr::summarise(count = n()) %>%
    tidyr::pivot_wider(id_cols = "region_id",
                       names_from = "type",
                       values_from = "count")
  pi_data[, c('apetitive', 'aversive')][is.na(pi_data[, c('apetitive', 'aversive')])] <- 0
  
  pi_data_summ <- pi_data %>%
    dplyr::ungroup() %>%
    dplyr::nest_by(region_id) %>%
    dplyr::summarise(preference_index = preference_index(data, min_exits_required = min_exits_required)) %>%
    dplyr::ungroup()
  
  
  # na should be 0 in this case
  pi_data <- dplyr::full_join(pi_data, pi_data_summ)
  
  
  gg <- idoc_plot(experiment_folder, roi_data, controller_data,
                  preference_data, pi_data,
                  CSplus=CSplus, CSminus=CSminus, border=border, ...)
  
  # browser()
  data.table::fwrite(x = pi_data, file = output_path_maker(experiment_folder, 'PI'))
  
  return(list(gg = gg, pi = pi_data))
}
