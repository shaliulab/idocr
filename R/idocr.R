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
                  ...) {
  
  document_script(src_file, experiment_folder)

  message("Loading dataset <- ", experiment_folder)
  dataset <- load_dataset(experiment_folder)
  
  message("Preprocessing dataset - ", experiment_folder)
  dataset <- preprocess_dataset(
    experiment_folder, dataset,
    treatments=treatments, delay=delay,
    border_mm=border_mm, CSplus_idx
  )
  
  message("Analysing dataset - ", experiment_folder)
  analysis <- analyse_dataset(
    dataset,
    min_exits_required=min_exits_required,
    min_time=mask_duration,
    analysis_mask=analysis_mask
  )

  message("Plotting dataset -> ", experiment_folder)
  gg <- plot_dataset(experiment_folder, dataset, analysis, analysis_mask=analysis_mask, ...)
  
  message("Exporting results -> ", experiment_folder)
  export_dataset(experiment_folder = experiment_folder,
                 dataset = dataset, analysis = analysis)
  
  return(list(gg = gg, pi = analysis$pi))
}


