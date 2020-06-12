#' Parse side from the hardware name
#' 
#' Return -1 for left and 1 for right
#'
#' @importFrom stringr str_match
#' @import magrittr
parse_side <- function(hardware) {
  hardware_side <- map(hardware, 
    ~c(
      stringr::str_match(pattern = "RIGHT", string = .)[, 1],
      stringr::str_match(pattern = "LEFT", string = .)[, 1]
      )
  ) %>%
    map_chr(~na.omit(unlist(.)))
  
  mapping <- c("LEFT" = -1, "RIGHT" = 1)
  hardware_side <- mapping[hardware_side]
  
  return(hardware_side)
}
