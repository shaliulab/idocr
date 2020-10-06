#' @importFrom  glue glue
document_script <- function(src_file, experiment_folder) {
  
  dst_file <- file.path(
    experiment_folder,
    "script.R"
  )
  message(glue::glue('Backing up script to {dst_file}'))
  file.copy(from = src_file, to = dst_file, overwrite = TRUE)
  
}