#' The standard idocr workflow.
#' 
#' Load data from the experiment folder, possibly with some specific settings
#' and return a data frame with the appetitive index of each fly
#' and a plot visualizing the experiment
#' @eval document_experiment_folder()
#' @eval document_delay()
#' @param mask_duration Seconds of behavior to be ignored after last cross,
#' so the same cross is not counted more than once due to noise in
#' the border cross
#' @param analysis_mask Named list of numeric vectors specifying
#' the start and end time in seconds of a period of the experiment that should
#' be analyzed separately
#' @inherit load_systematic_rois
#' @param ... Extra arguments to plot_dataset
#' @inherit document_script
#' @inherit preprocess_controller
#' @inherit find_exits
#' @inherit preprocess_dataset
#' @inherit analyse_dataset
#' @importFrom data.table fwrite
#' @seealso [load_dataset()]
#' @seealso [preprocess_dataset()]
#' @seealso [analyse_dataset()] 
#' @seealso [plot_dataset()]
#' @seealso [export_dataset()]
#' @export
idocr <- function(experiment_folder,
                  treatments=paste0("TREATMENT_", c("A", "B")),
                  min_exits_required = 5,
                  CSplus_idx=1,
                  border_mm = 5,
                  delay = 0,
                  src_file = NULL,
                  mask_duration = 0.5,
                  analysis_mask = NULL,
                  n=20,
                  ...) {
  
  document_script(src_file, experiment_folder)

  message("Loading dataset <- ", experiment_folder)
  dataset <- load_dataset(experiment_folder, n=n)
  
  message("Preprocessing dataset - ", experiment_folder)

  dataset <- preprocess_dataset(
    experiment_folder, dataset,
    treatments=treatments, delay=delay,
    border_mm=border_mm, CSplus_idx=CSplus_idx
  )

  result <- list()
  
  if (is.null(analysis_mask)) {
    result[[1]] <- pipeline(experiment_folder, dataset,
                       min_exits_required,
                       mask_duration, ...)
  } else {
    result <- list()
    for (i in 1:length(analysis_mask)) {
      partial_result <- pipeline(experiment_folder, dataset,
                                 min_exits_required,
                                 mask_duration,
                                 analysis_mask = analysis_mask[i], ...)
      result[[i]] <- partial_result
      i <- i + 1
    }
    names(result) <- names(analysis_mask)
  }
  
  return(result)
}


#' Analyse plot and export dataset
#' 
#' @inherit analyse_dataset
#' @inherit plot_dataset
#' @inherit export_dataset
#' @param mask_duration Exits happening this amount of seconds after the last one are ignored
#' @param ... Extra arguments to plot_dataset
pipeline <- function(experiment_folder, dataset, min_exits_required, mask_duration, analysis_mask=NULL, ...) {
  
  
  if(is.null(analysis_mask)) {
    result_folder <- experiment_folder
    suffix <- ""
  } else {
    if(length(names(analysis_mask)) < 1) stop("Please provide a name to every analysis mask")
    result_folder <- file.path(experiment_folder, names(analysis_mask))
    suffix <- names(analysis_mask)
    if (! dir.exists(result_folder)) dir.create(result_folder)
  }
  
  message("Analysing dataset - ", experiment_folder, " ", suffix)
  
  analysis <- analyse_dataset(
    dataset,
    min_exits_required=min_exits_required,
    min_time=mask_duration,
    analysis_mask=analysis_mask
  )
  
  message("Plotting dataset -> ", experiment_folder)
  out <- plot_dataset(experiment_folder, dataset, analysis, result_folder=result_folder, analysis_mask=analysis_mask, suffix=suffix, ...)
  plot_paths <- out$paths
  gg <- out$gg
  
  message("Exporting results -> ", experiment_folder)
  out <- export_dataset(experiment_folder = experiment_folder,
                        dataset = dataset, analysis = analysis,
                        result_folder=result_folder,
                        suffix=suffix
  )
  csv_paths <- out$paths
  return(list(gg = gg, pi = analysis$pi, paths = c(plot_paths, csv_paths)))
}
