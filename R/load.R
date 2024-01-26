#' Confirm VAR_MAP csv table is not corrupted
#' @param var_map_path Path to a VAR_MAP table .csv file
validate_varmap_file <- function(var_map_path) {
  return(0)
}

#' Load the VAR_MAP table into R
#' 
#' @importFrom data.table fread
#' @eval document_experiment_folder()
load_varmap <- function(experiment_folder) {
  var_map_path <- find_file(experiment_folder, "VAR_MAP")
  stopifnot(length(var_map_path) > 0)
  validate_varmap_file(var_map_path)
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

#' Check whether the user is running deprecated code
#' 
#' @eval document_treatments()
check_api_version <- function(treatments) {
  treatment_in_name <- length(grep(pattern = "TREATMENT", x = names(treatments))) != 0
  # treatment_not_in_value <- length(grep(pattern = "TREATMENT", x = names(treatments))) != 0
  
  if (treatment_in_name) {
    warning("Passing named treatments is deprecated.
            Your code will still work fine, but you should provide the treatment name
            (OCT, ...) via the labels argument in idocr::idocr.
            In that case, the labels are assigned in alphabetic order to the treatments
            i.e. the first label goes to TREATMENT_A and the second to B
            ")
    return(1)
  } else {
    return(2)
  }
}


#' Preprocess a RAW idoc dataset
#' 
#' 1. Preprocess tracker and controller data
#' 2. Features expected by the analysis functions
#' are only available after some minor computations in the raw data
#' @eval document_experiment_folder()
#' @eval document_dataset()
#' @eval document_treatments()
#' @param border_mm mm from center of chamber to decision zone edge
#' @param CSplus_idx Whether the first treatment (CSplus_idx=1) or the second
#' (CSplus_idx=2) is associated with appetitive behavior
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
  
  config <- read_config()
  pixel_to_mm_ratio <- config$pixel_to_mm_ratio
  dataset$limits <- config$limits

  border <- border_mm * pixel_to_mm_ratio
  treatments <- names(treatments)
  dataset$labels <- unname(treatments)
  
  # if (check_api_version(treatments) == 1) {
  #   dataset$labels <- unname(treatments)
  #   treatments <- names(treatments)
  # }
  
  dataset$border <- border
  dataset$CSplus <- treatments[CSplus_idx]
  dataset$CSminus <- treatments[treatments != dataset$CSplus]
  dataset$treatments <- treatments
  dataset$stimuli <- paste0(rep(treatments, each=2), c("_LEFT", "_RIGHT"))
  
  return(dataset)
}

#' Load an IDOC .csv dataset
#' 
#' Load the .csv database available at the passed directory
#' @eval document_experiment_folder()
#' @inherit load_systematic_rois
#' @export
load_dataset <- function(experiment_folder, n=20) {
  # Load tracker data (ROI - Region of Interest)
  tracker_data <- load_systematic_rois(experiment_folder, n=n)
  
  # Load controller data
  ## Wide format table where every piece of stimulus has a column and the values are 1 or 0
  ## An extra column called t tells the time in seconds
  controller_data <- load_controller(experiment_folder)
  
  dataset <- list(tracker=tracker_data, controller=controller_data)
  return(dataset)
}
