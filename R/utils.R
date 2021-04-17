eucl_dist <- function(p1, p2) {
  sqrt(sum((p1 - p2)**2))
}


wrap_quotes <- function(x) {
  stopifnot(class(x) == "character")
  paste0('"', x, '"')
}

#' Parse side from the stimulus name
#' 
#' Return -1 for left and 1 for right
#'
#' @importFrom stringr str_match
#' @importFrom purrr map_chr map
#' @importFrom magrittr `%>%`
#' @param stimulus Name of stimulus to be parsed.
#' Must contain LEFT or RIGHT on its name
parse_side <- function(stimulus) {
  
  stopifnot(grep(pattern = "LEFT", x = stimulus) |  grep(pattern = "RIGHT", x = stimulus))
  side <- purrr::map(stimulus, 
                     ~c(
                       stringr::str_match(pattern = "RIGHT", string = .)[, 1],
                       stringr::str_match(pattern = "LEFT", string = .)[, 1]
                     )
  ) %>%
    purrr::map_chr(~na.omit(unlist(.)))
  
  mapping <- c("LEFT" = -1, "RIGHT" = 1)
  side <- mapping[side]
  
  return(side)
}

#' @importFrom stringr str_remove
remove_side <- function(stimulus) {
  
  . <- NULL
  
  stopifnot(grep(pattern = "LEFT", x = stimulus) |  grep(pattern = "RIGHT", x = stimulus))
  treatment <- lapply(stimulus, 
                     function(x) {
                       stringr::str_remove(pattern = "_RIGHT", string = x) %>%
                       stringr::str_remove(pattern = "_LEFT", string = .)
                     })
  return(treatment)
}

#' Return system time unless testing
idocr_time <- function() {
  
  is_testing <- testthat_is_testing()
  
  if (is_testing) {
    time <- as.POSIXct("2021-01-01 00:00:01 CEST")
  } else {
    time <- Sys.time()  # nocov
  }
  return(time)
}
  
testthat_is_testing <- function() {
  is_testing <- FALSE
  
  # is testing will be true only if
  # testthat is installed in the system
  # AND
  # we are actually testing
  is_testing <- tryCatch(
    testthat::is_testing(),
    error = function(e) FALSE
  )
  
  return(is_testing)
}

#' Convenience wrapper around data.table::fwrite with preferred defaults
#' @importFrom data.table fwrite
#' @inherit data.table::fwrite
#' @param ... Extra arguments to data.table::fwrite
#' @seealso [data.table::fwrite()]
fwrite_ <- function(x, file, sep=",", na="NA", col.names=TRUE, ...) {
  data.table::fwrite(x = x,
                     file = file,
                     sep = sep,
                     na = na,
                     col.names = col.names,
                     ...)
}

#' Make sure the passed csv file has same number of fields on every row
#' @param csv_file Path to a .csv file produced by IDOC
#' @importFrom stringr str_count
#' @importFrom magrittr `%>%`
validate_number_of_fields <- function(csv_file) {
  
  nfields <- lapply(readLines(csv_file), function(x) stringr::str_count(x, pattern = ",")) %>%
    unlist
  
  tabl <- table(nfields)
  
  if (length(tabl) != 1) {
    correct_n_fields <- names(tabl[(length(tabl))])
    tabl <- tabl[-(length(tabl))]
    corruped_rows <- which(nfields %in% names(tabl))
    
    if (requireNamespace("emo", quietly=T)) {
      error_message <- paste0("
                Corrupted file -> ", csv_file, " ", emo::ji("shit"), ".",
                              "
                Following rows have a number of fields different from the rest (",
                              correct_n_fields, "): Rows ", paste(corruped_rows, collapse=" and "), ". ",
                              "
                Header counts as first row. Please correct this file so all rows have same number of fields (",
                              correct_n_fields, ") ", emo::ji("warning"), ".",
                              "
                You can do that by opening the file with Libreoffice Calc or MS Office Excel
                and checking that all rows have equal number of cells.
                Report to the package maintainer if you cannot solve this
                by opening an issue here: https://github.com/shaliulab/idocr/issues ", emo::ji("thanks")
      )
    } else {
      error_message <- paste0("
                Corrupted file -> ", csv_file, ".",
                              "
                Following rows have a number of fields different from the rest (",
                              correct_n_fields, "): Rows ", paste(corruped_rows, collapse=" and "), ". ",
                              "
                Header counts as first row. Please correct this file so all rows have same number of fields (",
                              correct_n_fields, ").",
                              "
                You can do that by opening the file with Libreoffice Calc or MS Office Excel
                and checking that all rows have equal number of cells.
                Report to the package maintainer if you cannot solve this
                by opening an issue here: https://github.com/shaliulab/idocr/issues "
      )
    }
    
    stop(error_message)
         
  } 
}