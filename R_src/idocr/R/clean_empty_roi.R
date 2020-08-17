#' Undo the effect of add_empty_roi
#' @importFrom purrr keep
#' @importFrom dplyr group_by group_split
#' @import magrittr
clean_empty_roi <- function(roi_data) {
  roi_data <- roi_data %>%
    dplyr::group_by(id) %>%
    dplyr::group_split(.) %>%
    purrr::keep(~nrow(.) > 100) %>%
    do.call(rbind, .)
  
  return(roi_data)
}
