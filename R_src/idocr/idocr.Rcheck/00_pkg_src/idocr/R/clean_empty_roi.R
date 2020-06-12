#' Undo the effect of add_empty_roi
clean_empty_roi <- function(roi_data) {
  roi_data <- roi_data %>%
    group_by(id) %>%
    group_split(.) %>%
    keep(~nrow(.) > 100) %>%
    do.call(rbind, .)
  
  return(roi_data)
}
