CONFIG_FILE <- "analysis_params.yaml"
DEFAULT_CONFIG <- list(pixels_to_mm_ratio = 2.3)
read_config <- function() {
  
  if (file.exists(CONFIG_FILE)) {
      config <- yaml::read_yaml(CONFIG_FILE)
  } else {
     config <- DEFAULT_CONFIG
  }
  return(config)
}