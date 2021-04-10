#' The standard idocr workflow.
#' 
#' Load data from the experiment folder, possibly with some specific settings
#' and return a data frame with the appetitive index of each fly
#' and a plot visualizing the experiment
#' @eval document_experiment_folder()
#' @param treatments Vector of treatments. You are likely to always pass TREATMENT_A and TREATMENT_B
#' @param border_mm Distance between arena center
#' and one border of the decision zone (mm)
#' @param min_exits_required Minimal number of exits
#' to be considered for significance
#' @param CSplus Name of treatment associated to appetitive conditioning
#' @eval document_delay()
#' @param mask_duration Seconds of behavior to be ignored after last cross,
#' so the same cross is not counted more than once due to noise in
#' the border cross
#' @inheritParams document_script
#' @inheritParams preprocess_controller
#' @importFrom data.table fwrite
#' @seealso load_dataset 
#' @seealso preprocess_dataset
#' @seealso analyse_dataset 
#' @seealso plot_dataset 
#' @seealso export_dataset
#' @export
idocr <- function(experiment_folder,
                  treatments=paste0("TREATMENT_", c("A", "B")),
                  min_exits_required = 5,
                  CSplus_idx=1,
                  border_mm = 5,
                  delay = 0,
                  src_file = NULL,
                  mask_duration = 0.5,
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
    min_time=mask_duration
  )

  message("Plotting dataset -> ", experiment_folder)
  gg <- plot_dataset(experiment_folder, dataset, analysis, ...)
  
  message("Exporting results -> ", experiment_folder)
  export_dataset(experiment_folder = experiment_folder,
                 dataset = dataset, analysis = analysis)
  
  return(list(gg = gg, pi = analysis$pi))
}


