#' Return list of ROI .csv files in the passed experiment folder
#' Paths are absolute
#' @eval document_experiment_folder()
#' @importFrom gtools mixedsort
find_rois <- function(experiment_folder) {
  # keep the ROI_* files only and in numerical order i.e. 10 after 9 and not after 1
  csv_files <- list.files(path = experiment_folder, pattern = ".csv", full.names = TRUE)
  # sort so ROI_10 goes after ROI_2
  roi_files <- gtools::mixedsort(grep(pattern = "ROI_\\d{1,2}", x = csv_files, value = T, ))
  return(roi_files)
}

#' Center the trace of movement along x axis so x=0 is set
#' at the center of the chamber
#' Estimating the center via Computer Vision is very costly because the center
#' does not look similar across chambers (some chambers are wider than others, etc)
#' For that reason, if you as user wish maximum accuracy,
#' you should run the midline-detector/main.py script, available here
#' https://github.com/shaliulab/midline-detector
#' like so:
#' python main <--experiment-folder EXPERIMENT_FOLDER> 
#' @eval document_tracker_data()
#' @eval document_experiment_folder()
#' @param infer If false, read coords of roi centers from ROI_CENTER file
#' otherwise estimate based on fly behavior
#' @importFrom dplyr left_join select
center_dataset <- function(experiment_folder, tracker_data, infer=FALSE) {
  # TODO Should we infer the min/max from the data
  # or rather hardcode them?
  
  if (infer) {
    x <- tracker_data$x
    x <- x - min(x)
    x <- x - max(x) / 2
    tracker_data$x <- x
  } else {
    roi_center <- get_roi_center(experiment_folder)
    tracker_data <- dplyr::left_join(tracker_data, roi_center, by="region_id")
    tracker_data$x <- tracker_data$x - tracker_data$center
    tracker_data <- tracker_data %>% dplyr::select(-center)
  }
  return(tracker_data)
}

#' Read the x coordinate of the center of the rois
#' This is useful for precise delineation of the decision zone
#' The function expects the ROI_CENTER and ROI_MAP files to exist
#' @eval document_experiment_folder()
#' @importFrom dplyr left_join select
#' @importFrom data.table fread
get_roi_center <- function(experiment_folder) {
  
  roi_center_file <- grep(x = list.files(experiment_folder, full.names = TRUE), pattern = "ROI_CENTER", value = T)
  roi_map_file <- grep(x = list.files(experiment_folder, full.names = TRUE), pattern = "ROI_MAP", value = T)
  
  if (length(roi_center_file) == 0) {
    warning("Please execute mindline-detector and save a ROI_CENTER.csv file in the folder")
    roi_center <- data.table(region_id=1:20, center=0)
  } else {
    roi_center <- data.table::fread(roi_center_file)
    if (any(roi_center$center == 0)) {
      warning("I found a ROI_CENTER file but it is not correct.
              Please check again a non-zero center is available for all ROIs"
      )
    }
    roi_map <- data.table::fread(roi_map_file)
    roi_map$region_id <- roi_map$value
    roi_center <- dplyr::left_join(roi_center, dplyr::select(roi_map, x, region_id), by="region_id")
    roi_center$center <- roi_center$center - roi_center$x
    roi_center <- dplyr::select(roi_center, -x)
  }
  return(roi_center)
}


#' Give each animal a unique id based on the run id of the experiment/machine
#' and its position on the machine#' 
#' @importFrom stringr str_pad
#' @eval document_experiment_folder()
#' @param region_id Position of the animal in the machine
construct_animal_id <- function(experiment_folder, region_id) {
  
  field <- value <- NULL
  metadata <- load_metadata(experiment_folder)
  run_id <- metadata[field == "run_id", value]
  id <- paste0(run_id, "|", stringr::str_pad(
    string = region_id, width = 2, side = "left", pad = "0"
  )
  )
  return(id)
}

#' Read a single ROI csv file
#' @importFrom stringr str_match
#' @importFrom data.table fread
#' @importFrom magrittr `%>%`
#' @param file Path to a file in an IDOC .csv database
read_roi <- function(file) {
  
  match <- stringr::str_match(file, pattern = ".*ROI_(\\d{1,2}).csv")
  idx <- as.integer(match[,2])
  tracker_data <- data.table::fread(file, header = T)[, -1] %>%
    cbind(file, region_id = idx)
  
  if (nrow(tracker_data) > 10) {
    return(tracker_data)
  } else {
    return(NULL)
  }
}

#' Remove duplicate entries in a data table
#' Duplicates have same region_id and t
#' @eval document_tracker_data()
#' @importFrom dplyr select
#' @importFrom magrittr `%>%`
remove_duplicates <- function(tracker_data) {
  
  region_id <- t <- . <- NULL
  tracker_data <- tracker_data[
    tracker_data %>%
      dplyr::select(region_id, t) %>%
      duplicated %>%
      !.,
  ]
  return(tracker_data)
}


keep_needed_columns_only <- function(experiment_folder, tracker_data) {
  var_map <- load_varmap(experiment_folder)
  tracker_data <- tracker_data[, c(var_map$var_name, names(get_extra_columns())), with=F]  
}


#' Preprocess raw tracker data
#' * Add a unique identifier to each animal
#' * Center the space coordinates around 0
#' * Keep only the needed columns
#' @eval document_experiment_folder()
#' @eval document_tracker_data()
#' @return tracker_data
preprocess_tracker <- function(experiment_folder, tracker_data) {
  # construct the id of the flies
  tracker_data$id <- construct_animal_id(experiment_folder, tracker_data$region_id)
  
  # center the data around the median
  # i.e. estimate the center of the chamber using the median (central) x
  tracker_data <- center_dataset(experiment_folder, tracker_data, infer=FALSE)
  
  # keep only needed columns
  tracker_data <- keep_needed_columns_only(experiment_folder, tracker_data)
  
  return(tracker_data)    
}

#' Load data in ROI csv tables into a single R tibble
#' 
#' Data saved by IDOC to .csv files needs to be read into R
#' @importFrom tibble as_tibble
#' @importFrom magrittr `%>%`
#' @return tibble
#' @param experiment_folder Path to a folder with IDOC results
#' @export
load_rois <- function(experiment_folder) {
  
  . <- NULL
  
  # link .csv files
  roi_files <- find_rois(experiment_folder)
  
  # read them into a single tibble
  tracker_data <- roi_files %>%
    # read the data into R
    lapply(X = ., FUN = read_roi) %>%
    # rbind all the separate data.tables into a single one
    do.call(what = rbind, .) %>%
    # cast the one data.table into a tibble
    tibble::as_tibble(.)
  
  if (nrow(tracker_data) < 10) {
    return(NULL)
  }
  
  # remove data points with same region_id and t
  # TODO Do they happen?
  tracker_data <- remove_duplicates(tracker_data)
  return(tracker_data)
}


#' Represent missing ROIs in the dataset with a single row
#' 
#' This is necessary so the results are always for 20 channels
#' regardless of whether the channel had an animal or not.
#' Doing so makes the results systematic and easily comparable across runs
#' @eval document_experiment_folder()
#' @eval document_tracker_data()
#' @param n Number of ROIS the output must have (empty or not) 
#' @importFrom tibble as_tibble
#' @export
add_empty_roi <- function(experiment_folder, tracker_data, n=20) {
  
  . <- sql_type <- NULL
  
  var_map <- load_varmap(experiment_folder)
  R_types <- list("SMALLINT" = integer, "BOOLEAN" = logical, "INT" = integer)
  tracker_data_template <- var_map[, map(sql_type, ~R_types[[.]](length=1))]
  names(tracker_data_template) <- var_map$var_name
  
  # replicate the addition of extra columns
  # (beyond those generated by the tracker)
  extra_columns <- get_extra_columns()
  for (i in 1:length(extra_columns)) {  
    column_name <- names(extra_columns)[[i]]
    tracker_data_template[[column_name]] <- extra_columns[[i]]
  }
  
  tracker_data_template <- as_tibble(tracker_data_template)
  
  missing_columns  <- colnames(tracker_data)[!colnames(tracker_data) %in% colnames(tracker_data_template)]
  for (mc in missing_columns) {
    tracker_data_template[, mc] <- NA
  }
  missing_columns  <- colnames(tracker_data)[!colnames(tracker_data) %in% colnames(tracker_data_template)]
  
  for (roi in 1:n) {
    if (!roi %in% unique(tracker_data$region_id)) {
      message(sprintf("Animal %s is missing", roi))
      local_template <- copy(tracker_data_template)
      local_template$region_id <- roi
      tracker_data <- rbind(tracker_data, local_template)
    }
    
  }
  return(tracker_data)
}

#' Load data from n channels
#' and expose missing data if needed 
#' @param ... Arguments to load_rois
#' @param n Number of channels desired.
#' If less than this amount of animals is found, idocr
#' will make up animals until this amount is hit
#' It (should match nrow x ncol of layout passed in the idocr function)
#' @return tibble
#' @export
#' 
load_systematic_rois <- function(..., n=20) {
  tracker_data <- load_rois(...)
  tracker_data <- add_empty_roi(..., tracker_data, n=n)
  return(tracker_data)
}



#' Undo the effect of add_empty_roi
#' 
#' Useful to remove dummy rois or rois with noise
#' Works only if not testing. During testing
#' we may want to pass small (noise-like) datasets
#' @importFrom purrr keep
#' @importFrom dplyr group_by group_split
#' @importFrom magrittr `%>%`
#' @eval document_tracker_data()
#' @param minimum Minimum number of datapoints in a row to be considered
#' not sparse (not noise) and thus valid
remove_empty_roi <- function(tracker_data, minimum=100) {
  
  id <- . <- NULL
  
  # check whether this is running in a testing environment
  # if testthat cannot be loaded, assume we are not testing
  testing <- testthat_is_testing()
  
  if (!testing) {
    tracker_data <- tracker_data %>%
      dplyr::group_by(id) %>%
      dplyr::group_split(.) %>%
      purrr::keep(~nrow(.) > minimum) %>%
      do.call(rbind, .)    
  }
  
  return(tracker_data)
}

#' TODO
get_extra_columns <- function() {
  extra_columns <- list(
    id = character(length = 1),
    t = numeric(length = 1),
    region_id = integer(length = 1)
  )
  
  return(extra_columns)
}


