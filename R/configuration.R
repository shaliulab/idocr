CONFIG_FILE <- "analysis_params.yaml"
DEFAULT_CONFIG <- list(pixel_to_mm_ratio = 2.3)
#' @importFrom yaml read_yaml
#' @import glue
#' @export
read_config <- function() {
  if (file.exists(CONFIG_FILE)) {
      message(glue::glue("Reading configuration from {CONFIG_FILE}"))
      config <- yaml::read_yaml(CONFIG_FILE)
  } else {
    message(glue::glue("{CONFIG_FILE} not found. Using default config"))
     config <- DEFAULT_CONFIG
  }
  return(config)
}
