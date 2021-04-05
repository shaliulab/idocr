#' The standard idocr workflow.
#' 
#' Load data from the experiment folder, possibly with some specific settings
#' and return a data frame with the appetitive index of each fly
#' and a plot visualizing the experiment
#' @eval document_experiment_folder()
#' @param treatments Named vector where names should match hardware (without side annotation) and value is a meaningful name for a treatment
#' example: c(TREATMENT_A = "OCT")
#' @param border_mm Distance between arena center
#' and one border of the decision zone (mm)
#' @param min_exits_required Minimal number of exits
#' to be considered for significance
#' @param CSplus Name of treatment associated to appetitive conditioning
#' @param delay Seconds to shift the representation of the treatments
#' on the plot to account for a latency or lag between treatment
#' delivery start and arrival to behavioral arena
#' @inheritParams document_script
#' @param mask_duration Seconds of behavior to be ignored after last cross,
#' so the same cross is not counted more than once due to noise in
#' the border cross
#' @importFrom data.table fwrite
#' @export
idocr <- function(experiment_folder, treatments,
                  border_mm = 5, min_exits_required = 5,
                  CSplus="TREATMENT_A", delay = 0,
                  src_file = NULL, mask_duration = 0.5,
                  ...) {
  
  document_script(src_file, experiment_folder)
  # Convert human understandable mm
  # to pixels that are easy to work with in R
  pixel_to_mm_ratio <- 2.3
  border <- border_mm * pixel_to_mm_ratio
  
  message("Loading dataset -> ", experiment_folder)
  dataset <- load_dataset(experiment_folder, delay=delay)
  dataset$border <- border
  dataset$CSplus <- CSplus
  dataset$CSminus <- grep(
    x = paste0("TREATMENT_", c("A", "B")),
    invert = TRUE, value = TRUE,
    pattern = CSplus
  )
  
  message("Analyzing dataset -> ", experiment_folder)
  analysis <- analyse_dataset(
    dataset,
    min_exits_required=min_exits_required,
    min_time=mask_duration
  )

  message("Plotting dataset -> ", experiment_folder)
  gg <- plot_dataset(experiment_folder, dataset, analysis, ...)
  
  data.table::fwrite(x = analysis$pi, file = output_path_maker(experiment_folder, 'PI'))
  
  return(list(gg = gg, pi = analysis$pi))
}


