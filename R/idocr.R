#' The standard idocr workflow.
#' 
#' Load data from the experiment folder, possibly with some specific settings
#' and return a data frame with the apetitive index of each fly
#' and a plot visualizing the experiment
#' @param treatments Named vector where names should match hardware (without side annotation) and value is a meaningful name for a treatment
#' example: c(TREATMENT_A = "OCT")
#' @import ggplot2
#' @importFrom purrr map
#' @importFrom data.table fwrite
#' @export
idocr <- function(experiment_folder, treatments, hardware = c("TREATMENT_A_LEFT",  "TREATMENT_A_RIGHT", "TREATMENT_B_LEFT",  "TREATMENT_B_RIGHT"),
                  border_mm = 5, min_exits_required = 5, CSplus="TREATMENT_A", delay = 0,
                  src_file = NULL, mask_duration = 0.5,
                  ...) {
  
  document_script(src_file, experiment_folder)

  
  # Convert human understandable mm
  # to pixels that are easy to work with in R
  pixel_to_mm_ratio <- 2.3
  border <- border_mm * pixel_to_mm_ratio
  
  # Load tracking data (ROI - Region of Interest)
  roi_data <- load_rois(experiment_folder)
  roi_data <- add_empty_roi(experiment_folder, roi_data, n = 20)
  
  # Load controller data
  ## Wide format table where every piece of hardware ahs a column and the values are 1 or 0
  ## An extra column called t tells the time in seconds
  controller_data <- load_controller(experiment_folder, delay = delay)
  limits <- c(min(roi_data$x), max(roi_data$x))
  
  rectangle_data <- define_rectangles(controller_data, hardware, limits)
  cross_data <- infer_decision_zone_exits(roi_data, border = border)

  side_agnostic_hardware <- sapply(
    hardware, function(x) strsplit(x, split = "_") %>%
      sapply(., function(y) paste0(y[1], "_", y[2]))) %>% 
    unique
  
  stopifnot(length(treatments[side_agnostic_hardware]) == length(side_agnostic_hardware))
  names(side_agnostic_hardware) <- treatments[side_agnostic_hardware]
  
  CSminus <- side_agnostic_hardware[side_agnostic_hardware != CSplus]
  
  # one row per exit
  preference_data <- compute_preference_data(cross_data, rectangle_data, CSplus, CSminus, mask_duration=mask_duration)
  # one row per fly with count of apetitive and aversive exits
  # as well as the computed preference index
  pi_data <- compute_pi_data(preference_data, min_exits_required = min_exits_required)

  gg <- idoc_plot(experiment_folder, roi_data, rectangle_data,
                  preference_data, pi_data,
                  CSplus = CSplus, CSminus = CSminus, border = border, limits = limits,
                  side_agnostic_hardware = side_agnostic_hardware, ...)
  
  data.table::fwrite(x = pi_data, file = output_path_maker(experiment_folder, 'PI'))
  
  return(list(gg = gg, pi = pi_data))
}
