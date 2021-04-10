#' Load the VAR_MAP table into R
#' 
#' @importFrom data.table fread
#' @eval document_experiment_folder()
load_varmap <- function(experiment_folder) {
  var_map_path <- find_file(experiment_folder, "VAR_MAP")
  var_map <- data.table::fread(var_map_path, header = T)[, -1]
  return(var_map)
}

#' Load the METADATA table into R
#' @importFrom data.table fread
#' @eval document_experiment_folder()
#' @export
load_metadata <- function(experiment_folder) {
  metadata_path <- find_file(experiment_folder, "METADATA")
  metadata <- data.table::fread(metadata_path, header = T)[,-1]
  return(metadata)
}

#' Preprocess a RAW idoc dataset
#' 
#' 1. Preprocess tracker and controller data
#' 2. Features expected by the analysis functions
#' are only available after some minor computations in the raw data
#' @eval document_experiment_folder()
#' @param dataset
#' @inherit preprocess_tracker
#' @inherit preprocess_controller
#' @export
preprocess_dataset <- function(
  experiment_folder, dataset,
  treatments = c("TREATMENT_A", "TREATMENT_B"),
  delay=0, border_mm=5, CSplus_idx=1
  ) {
  
  # Preprocess
  dataset$tracker <- preprocess_tracker(experiment_folder, dataset$tracker)
  dataset$controller <- preprocess_controller(dataset$controller, delay=delay)
  
  dataset$limits <- c(
    min(dataset$tracker$x),
    max(dataset$tracker$x)
  )
  
  pixel_to_mm_ratio <- 2.3
  border <- border_mm * pixel_to_mm_ratio
  dataset$border <- border
  dataset$CSplus <- treatments[1]
  dataset$CSminus <- treatments[treatments != dataset$CSplus]
  dataset$treatments <- treatments
  dataset$stimuli <- paste0(rep(treatments, each=2), c("_LEFT", "_RIGHT"))
  
  return(dataset)
}

#' Load an IDOC .csv dataset
#' 
#' Load the .csv database available at the passed directory
#' @eval document_experiment_folder()
#' @param ... Arguments to preprocess_dataset
#' @seealso [preprocess_dataset()]
#' @export
load_dataset <- function(experiment_folder) {
  # Load tracking data (ROI - Region of Interest)
  tracker_data <- load_systematic_rois(experiment_folder)
  
  # Load controller data
  ## Wide format table where every piece of hardware has a column and the values are 1 or 0
  ## An extra column called t tells the time in seconds
  controller_data <- load_controller(experiment_folder)
    
  dataset <- list(tracker=tracker_data, controller=controller_data)
  return(dataset)
}
