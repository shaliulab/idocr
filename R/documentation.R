#' Make a backup of a file
#' 
#' This is useful for keeping a documentation of the R code
#' used to produce some results based on some data
#' 
#' @param src_file Path of file to be copied.
#' If NULL, take current file (works on RStudio)
#' @param dst_folder Path of destination folder
document_script <- function(src_file=NULL, dst_folder) {
  
  dst_file <- file.path(
    dst_folder,
    "script_idocr2.R"
  )
  tryCatch(
    rstudioapi::documentSave(),
    error=function(e) {
      message("Running outside RStudio")
    }
  )

  message("Backing up script ->", dst_file)
  file.copy(from = src_file, to = dst_file, overwrite = TRUE)
}
