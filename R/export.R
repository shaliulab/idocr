#' Put the most important data into a wide format table
#' 
#' @importFrom tidyr pivot_wider
#' @importFrom magrittr `%>%`
#' @importFrom data.table fwrite
#' @importFrom dplyr select mutate
#' @importFrom gtools mixedsort
#' @eval document_controller_data()
#' @eval document_tracker_data()
#' @return data.table
#' @export
make_summary <- function(tracker_data, controller_data) {
  . <- region_id <- x <- NULL

  tracker_summary <- tracker_data %>%
    dplyr::select(t, x, region_id) %>%
    dplyr::mutate(region_id = paste0("ROI_", region_id)) %>%
    tidyr::pivot_wider(data = ., values_from = x, names_from = region_id)
  
  # make sure ROIs are placed in right order (1->20)
  tracker_summary <- tracker_summary[, gtools::mixedsort(colnames(tracker_summary))]
  
  # TODO Export var map of controller data in Python
  # for now just deselecting elapsed_seconds
  # This is fragile. If a new column is added to the
  # CONTROLLER_EVENTS table, this code could a bug
  
  # Interpolate the controller data by adding
  # one row for each frame that was analyzed
  controller_summary <- interpolate_controller(
    controller_data=controller_data,
    index=tracker_summary[, "t"]
  )

  summary_data <- dplyr::full_join(
    tracker_summary,
    controller_summary,
    on = "t"
  )
  
  summary_data <- format_summary(summary_data)
  return(summary_data)
}

format_summary <- function(x) {
  # summary_data[nrow(summary_data), ]
  # place t as the first column
  x <- x[, c("t", setdiff(colnames(x), "t"))]
  # summary_data <- summary_data[1:(nrow(summary_data)-1), ]
  return(x)
}

#' Export a single csv with all key data for analysis and plotting outside of R
#' 
#' @eval document_experiment_folder()
#' @param output_csv Path of csv output. If not provided,
#' @param ... Extra arguments to make_summary
#' @seealso [make_summary()]
#' a new file in the experiment folder with key SUMMARY is produced
export_summary_new <- function(experiment_folder, output_csv=NULL, ...) {
  
  summary_data <- make_summary(...)
  
  if(is.null(output_csv)) {
    output_csv <- build_filename(
      experiment_folder = experiment_folder,
      metadata = load_metadata(experiment_folder),
      key = "SUMMARY"
    )
  }
  
  message("Saving SUMMARY -> ", output_csv)
  
  fwrite_(summary_data, output_csv)
  

  return(summary_data)
}

#' Export a single csv with all key data for analysis and plotting outside of R
#' 
#' @eval document_experiment_folder()
#' @export
export_summary <- function(experiment_folder) {
  # .Deprecated()
  friendly_message <- "export_summary() is deprecated.
  Don't worry. This just means you don't need to run
  export_summary() anymore because
  it has been integrated into idocr().
  You can ignore this message!!"
  
  friendly_message <- tryCatch({
    friendly_message <- paste(
      friendly_message, emo::ji("relieved"), emo::ji("party"),
      sep = " "
    )
  }, error = function(e) {
    friendly_message
  })
  message(friendly_message)
}

#' Export the preference index to a csv file
#' 
#' @inherit export_summary
#' @param pi Dataframe to be exported.
#' Should contain a column named preference_index
#' @param output_csv Path of csv output. If not provided,
#' a new file in the experiment folder with key SUMMARY is produced
export_pi_summary <- function(experiment_folder, pi, output_csv=NULL) {
  
  if(is.null(output_csv)) {
    output_csv <- build_filename(
      experiment_folder = experiment_folder,
      metadata = load_metadata(experiment_folder), key = "PI"
    )
  }
  message("Saving PI -> ", output_csv)
  
  fwrite_(pi, output_csv)
  
  return(output_csv)
}

#' Export analysis results to experiment_folder
#' 
#' Generate the preference index table
#' Generate the summary table
#' @eval document_experiment_folder()
#' @eval document_dataset()
#' @eval document_analysis()
#' @param ... Extra argumetns to export_summary
#' @seealso [export_pi_summary()]
#' @seealso [export_summary()]
export_dataset <- function(experiment_folder, dataset, analysis, ...) {
  export_pi_summary(experiment_folder = experiment_folder, pi = analysis$pi)
  summary_data <- export_summary_new(
    experiment_folder = experiment_folder,
    tracker_data = dataset$tracker,
    controller_data = dataset$controller,
    ...
  )
  export_data <- list(summary=summary_data, pi = analysis$pi)
  return(export_data)
}
  