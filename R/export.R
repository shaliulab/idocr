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

  # keep the fields we want
  tracker_summary_long <- tracker_data %>%
    dplyr::select(t, x, region_id) %>%
    dplyr::mutate(region_id = paste0("ROI_", region_id))

  # cast to a wide table where each animal and stimulus gets its own column
  # each timepoint gets its own row
  tracker_summary <- tracker_summary_long %>% 
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
    by = "t"
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
#' @eval document_result_folder(required=FALSE)
#' @param output_csv Path of csv output. If not provided,
#' @eval document_suffix()
#' @param ... Extra arguments to make_summary
#' @seealso [make_summary()]
#' a new file in the experiment folder with key SUMMARY is produced
export_summary_new <- function(experiment_folder, result_folder=NULL, output_csv=NULL, suffix= "", ...) {

  if (is.null(result_folder)) result_folder <- experiment_folder

  summary_data <- make_summary(...)
  
  if(is.null(output_csv)) {
    output_csv <- build_filename(
      result_folder = result_folder,
      metadata = load_metadata(experiment_folder),
      key = "SUMMARY",
      suffix = suffix
    )
  }
  
  message("Saving SUMMARY -> ", output_csv)
  fwrite_(summary_data, output_csv)
  

  return(list(data=summary_data, path=output_csv))
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
#' @eval document_experiment_folder()
#' @eval document_result_folder(required=FALSE)
#' @param pi Dataframe to be exported.
#' Should contain a column named preference_index
#' @param output_csv Path of csv output. If not provided,
#' a new file in the experiment folder with key SUMMARY is produced
#' @eval document_suffix()
export_pi_summary <- function(experiment_folder, pi, result_folder=NULL, output_csv=NULL, suffix="") {
  
  if (is.null(result_folder)) result_folder <- experiment_folder
  
  if(is.null(output_csv)) {
    output_csv <- build_filename(
      result_folder = result_folder,
      metadata = load_metadata(experiment_folder),
      key = "PI",
      suffix = suffix
    )
  }
  message("Saving PI -> ", output_csv)
  
  pi$preference_index <- round(pi$preference_index, digits = 3)
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
#' @eval document_result_folder()
#' @eval document_suffix()
#' @param summary Whether to export a summary or not
#' @param ... Extra arguments to export_summary
#' @seealso [export_pi_summary()]
#' @seealso [export_summary()]
export_dataset <- function(experiment_folder, result_folder, dataset, analysis, suffix, ...) {
  pi_path <- export_pi_summary(experiment_folder = experiment_folder, result_folder=result_folder,pi = analysis$pi, suffix=suffix)
  out <- export_summary_new(
    experiment_folder = experiment_folder,
    tracker_data = dataset$tracker,
    controller_data = dataset$controller,
    result_folder = result_folder,
    suffix=suffix,
    ...
  )

  summary_data <- out$data
  summary_path <- out$path
  
  out <- list(summary=summary_data, pi = analysis$pi, paths = list(pi = pi_path, summary = summary_path))
  return(out)
}
