#' @importFrom tidyr pivot_wider
#' @importFrom magrittr `%>%`
#' @importFrom data.table fwrite
#' @importFrom dplyr select mutate
#' @eval document_experiment_folder()
#' @eval document_delay()
#' @param output_csv Path to output file.
#' If NULL (default), saved to experiment folder with key SUMMARY
#' @return data.table
#' @export
#'
make_summary <- function(tracking_data, controller_data) {
  . <- region_id <- x <- NULL

  tracking_summary <- tracking_data %>%
    dplyr::select(t, x, region_id) %>%
    dplyr::mutate(region_id = paste0("ROI_", region_id)) %>%
    tidyr::pivot_wider(data = ., values_from = x, names_from = region_id)
  
  # TODO Export var map of controller data in Python
  # for now just deselecting elapsed_seconds
  # This is fragile. If a new column is added to the
  # CONTROLLER_EVENTS table, this code could a bug
  
  # Interpolate the controller data by adding
  # one row for each frame that was analyzed
  controller_summary <- interpolate_controller(
    controller_data,
    tracking_summary[, "t"]
  )
  
  summary_data <- dplyr::full_join(
    tracking_summary,
    controller_summary,
    on = "t"
  )
  
  return(summary_data)
  
}
#' Export a single csv with all key data for analysis and plotting outside of R
export_summary <- function(experiment_folder, output_csv=NULL, ...) {
  
  summary_data <- make_summary(...)
  
  if(is.null(output_csv)) {
    output_csv <- build_filename(
      metadata = load_metadata(experiment_folder),
      key = "SUMMARY"
    )
  }
  
  data.table::fwrite(x = summary_data,
                     file = output_csv,
                     sep = ",",
                     col.names = TRUE)
  return(summary_data)
}

#' @importFrom data.table fwrite
export_pi_summary <- function(experiment_folder, pi, output_csv=NULL) {
  
  if(is.null(output_csv)) {
    output_csv <- build_filename(
      metadata = load_metadata(experiment_folder), key = "PI"
    )
  }
  
  data.table::fwrite(x = pi,
                     file = output_csv,
                     sep = ",", na = "NA",
                     col.names = TRUE)
  return(output_csv)
}

#' Export analysis results to experiment_folder
#' 
#' Generate the preference index table
#' Generate the summary table
#' @eval document_experiment_folder()
#' @eval document_dataset()
#' @eval document_analysis()
#' @importFrom data.table fwrite
export_dataset <- function(experiment_folder, dataset, analysis) {
  export_pi_summary(experiment_folder, analysis$pi)
  summary_data <- export_summary(dataset$tracking, dataset$controller)
  export_data <- list(summary=summary_data, pi = analysis$pi)
  return(export_data)
}
  