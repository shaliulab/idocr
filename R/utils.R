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
  
  is_testing <- FALSE
  
  # is testing will be true only if
  # testthat is installed in the system
  # AND
  # we are actually testing
  is_testing <- tryCatch(
    testthat::is_testing(),
    error = function(e) FALSE
  )
  
  if (is_testing) {
    time <- as.POSIXct("2021-01-01 00:00:01 CEST")
  } else {
    time <- Sys.time()
  }
  return(time)
}