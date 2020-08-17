#' Reshape the controller data to be plotted in ggplot2
#'
#' Given a table containing when several hardware turned on/off
#' during an experiment, and a piece of hardware,
#' prepare_shape_data will generate a table with one row per corner in a rectangle
#' encompassing all the area of the plot where the hardware is active
#' This is given by its side (X axis) and the time when it was on (Y axis)
#' If the hardware was turned on/off n times, we get n rectangles and thus n*4 rows.#' 
#' The x axis is assumed to go from -1 to 1. To scale it, see scale_shape
#' @importFrom stringr str_match
#' @importFrom purrr map_dbl
#' @import magrittr
#' @import data.table
prepare_shape_data <- function(controller_data, hardware = "LED_R_RIGHT") {
  
  hardware_side <- c(
    stringr::str_match(pattern = "RIGHT", string = hardware)[, 1],
    stringr::str_match(pattern = "LEFT", string = hardware)[, 1]
  ) %>%
    na.omit
  x_values <- list("LEFT" = c(-1, 0), "RIGHT" = c(0, 1))
  
  x_vals <- x_values[[hardware_side]]
  
  # TODO Make tibble for consistency
  hardware_events <- as.data.table(controller_data)[, c("t", hardware), with = F] %>%
    .[, hardware, with = F, drop = T] %>%
    unname %>%
    unlist %>%
    rev
  
  # make sure the off event is registered
  # if its not available in the controller data
  # assume it turned off at the last timestamp available
  # the last timestamp is first if reversed
  if (hardware_events[1] == 1) {
    hardware_events[1] <- 0
  }
  
  hardware_events <- hardware_events %>%
    rev %>%
    diff %>%
    c(0, .)
  
  all_events <- abs(hardware_events)
  
  if(sum(all_events) %% 2 != 0) {
    stop(sprintf("Problem parsing an end timestamp for %s", hardware))
  }
  
  switch_timestamps <- controller_data[as.logical(all_events), t]
  
  # we are making rectangles, so generate 2 extra points
  # for each pair of on-off events
  shape_data <- data.table(
    x = rep(rep(x_vals, times = 2), length(switch_timestamps) / 2),
    t = rep(round(switch_timestamps), each = 2)
  )
  
  # assign the blocks of 4 points to  single group (shape)
  shape_data$group <- 0:(nrow(shape_data) - 1) %/% 4
  
  # sort the block as expected by ggforce::geom_shape
  setkey(shape_data, "group")
  shape_data <- shape_data[, .SD[c(1, 2, 4, 3)]]
  
  # shape_data <- replicate(20, shape_data, simplify = FALSE) %>%
  #   purrr::imap(~cbind(.x, region_id = .y)) %>%
  #   do.call(rbind, .)
  
  return(shape_data)
}

#' Scale the x axis of a shape data table
#' using the x column of tracking data
#' scale_shape fetches the width of the chambers
#' and scales the shape accodingly
#' 
#' @importFrom purrr map
scale_shape <- function(shape_data, roi_data) {
  shape_data$x <- purrr::map_dbl(shape_data$x,
                          ~ifelse(
                            . == 1, . * max(roi_data$x), ifelse(
                              . == -1, . * min(roi_data$x), .
                            )
                          )
  )
  return(shape_data)
}

