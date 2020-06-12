#' @importFrom data.table fread
load_varmap <- function(experiment_folder) {
  
  csv_files <- list.files(path = experiment_folder, pattern = ".csv")
  var_map_filename <- grep(pattern = "VAR_MAP", x = csv_files, value = T)
  var_map_path <- file.path(experiment_folder, var_map_filename)
  var_map <- data.table::fread(file = var_map_path, header = T)[, -1]
  return(var_map)
}

