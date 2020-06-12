#' @importFrom tibble tibble
cross_detector <- function(roi_data, border, side=1) {
  
  length_encoding <- rle((roi_data$x * side) > border)
  
  cross_data <- tibble(
    lengths = length_encoding$lengths,
    beyond = length_encoding$values,
    index = cumsum(length_encoding$lengths)
  )
  
  cross_data$t_ms <- roi_data[cross_data$index, ]$t_ms
  cross_data <- cross_data[, c("t_ms", "beyond")]
  cross_data$border <- border
  cross_data$side <- side
  
  return(cross_data)
}


# TODO
# Make this a test
# is_cross(roi_data[roi_data$region_id == 10, ], border = 10, side = 1)

#' @importFrom purrr map
#' @importFrom tibble as_tibble
#' @import magrittr
gather_cross_data <- function(cross_detector_FUN = cross_detector, roi_data, border, side) {
  cross_data <- unique(clean_empty_roi(roi_data)$id) %>%
    purrr::map(
      ~cbind(
        id = .,
        region_id = unique(roi_data[roi_data$id == ., "region_id"]),
        roi_data[roi_data$id == ., ] %>% cross_detector_FUN(., border = border, side = side)
      )
    ) %>%
    do.call(rbind, .) %>%
    as_tibble
  
  cross_data$x <- cross_data$border * cross_data$side
  
  return(cross_data)
}
