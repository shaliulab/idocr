CONFIG_FILE <- "analysis_params.yaml"
DEFAULT_CONFIG <- list(pixel_to_mm_ratio = NULL, limits=c(NULL, NULL))
#' @importFrom yaml read_yaml
#' @import glue
#' @export
read_config <- function(file=NULL) {
  if (!is.null(file) && file.exists(file)) {
    message(glue::glue("Reading configuration from {file}"))
    config <- yaml::read_yaml(file)
  } else if (file.exists(CONFIG_FILE)) {
      message(glue::glue("Reading configuration from {CONFIG_FILE}"))
      config <- yaml::read_yaml(CONFIG_FILE)
  } else {
    message(glue::glue("{CONFIG_FILE} not found. Using default config"))
     config <- DEFAULT_CONFIG
     yaml::write_yaml(x = config, file=CONFIG_FILE)
  }
  stopifnot(!is.null(config$pixel_to_mm_ratio))
  stopifnot(!is.null(config$limits[1]))
  stopifnot(!is.null(config$limits[2]))
  
  return(config)
}
