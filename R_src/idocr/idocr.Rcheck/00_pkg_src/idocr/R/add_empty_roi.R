#' Represent missing ROIs in the dataset with a single row
#' 
#' This is done to show an empty facet that however fits
#' the expected 20 animals
#' @importFrom tibble as_tibble
add_empty_roi <- function(experiment_folder, roi_data) {
  
  var_map <- load_varmap(experiment_folder)
  R_types <- list("SMALLINT" = integer, "BOOLEAN" = logical, "INT" = integer)
  roi_data_template <- var_map[, map(sql_type, ~R_types[[.]](length=1))]
  names(roi_data_template) <- var_map$var_name
  roi_data_template <- as_tibble(
    cbind(
      id = character(length = 1),
      t_ms = numeric(length = 1),
      roi_data_template,
      region_id = integer(length = 1)
    )
  )
  
  for (roi in 1:20) {
    if (!roi %in% unique(roi_data$region_id)) {
      message(sprintf("Animal %s is missing", roi))
      local_template <- copy(roi_data_template)
      local_template$region_id <- roi
      roi_data <- rbind(roi_data, local_template)
    }
    
  }
}
