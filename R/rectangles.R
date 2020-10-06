#' Wrapper around define_rectangle for several hardware
#' 
#' @param controller_data A wide data.frame of hardware and a t column
#' @param hardware A character vector consisting of a subset of the columns in controller_data
#' for which rectangles describing the period when the hardware was on, should be built
define_rectangles <- function(controller_data, hardware, limits) {
  
  rect_pad <- 0
  
  ## Reformat the wide table
  ### We get one row for every corner of the rectangles shown on the plot
  ### to represent when the hardware items listed in `hardware`
  ### are on
  ### The row states:
  ### * x -> the position (-1,0,1) of the corner
  ### * side -> the side where the rectangle is (-1 if on the left and 1 if on the right)
  ### * hardware -> name of the hardware item
  ### * t_ms -> time in milliseconds
  
  controller_data <- purrr::map(
    hardware,
    ~define_rectangle(
      controller_data = controller_data,
      hardware = .
    )
  ) %>%
    do.call(rbind, .) %>%
    dplyr::mutate(t_ms = t * 1000)
  
  
  controller_data$hardware_small <- unlist(lapply(
    strsplit(controller_data$hardware_, split = "_"),
    function(x) {
      paste(x[1:2], collapse = "_")
    }))
  
  rectangle_data <- controller_data %>%
    dplyr::group_by(hardware_) %>%
    dplyr::group_split() %>%
    purrr::map(~scale_rectangle(., limits, rect_pad))
  
  return(rectangle_data)
}


#' Reshape the controller data to be plotted in ggplot2
#'
#' Given a table containing when several hardware turned on/off
#' during an experiment, and a piece of hardware,
#' prepare_shape_data will generate a table with one row per corner in a rectangle
#' encompassing all the area of the plot where the hardware is active
#' This is given by its side (X axis) and the time when it was on (Y axis)
#' If the hardware was turned on/off n times, we get n rectangles and thus n*4 rows.#' 
#' The x axis is assumed to go from -1 to 1. To scale it, see scale_shape
#' @importFrom purrr map_dbl
#' @import magrittr
#' @import data.table
#' @importFrom dplyr mutate case_when
#' @export
define_rectangle <- function(controller_data, hardware = "LED_R_LEFT") {
  
  ## Preprocessing
  # Detect side of hardware
  hardware_side <- parse_side(hardware)
  x_values <- list("-1" = c(-1, 0), "1" = c(0, 1))
  x_vals <- x_values[[as.character(hardware_side)]]
  
  # keep just time and the column for the current hardware
  controller_data <- controller_data[, c("t", hardware), with = F]
  
  # remove possible dups
  controller_data <- controller_data[!duplicated(controller_data), ]
  
  hardware_events <- controller_data[[hardware]] %>%
    # detect differences
    diff %>%
    # add something at the beginning
    # to align the differences with the original time series
    # a 0 means no change (which makes sense because it is t0)
    c(0, .)
  
  # the order with which
  # we diff and then add the 0
  # does NOT matter
  
  
  if (sum(hardware_events) != 0) {
    stop(sprintf("Problem parsing an end timestamp for %s", hardware))
  }
  
  # Pick the time at which this differences occur
  switch_timestamps <- controller_data[which(as.logical(abs(hardware_events))), t]
  
  if (length(switch_timestamps) %% 2 != 0) {
    stop(sprintf("Problem parsing an end timestamp for %s", hardware))
  }
  
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
  shape_data <- shape_data[, .SD[c(1, 2, 4, 3)], by = "group"]
  
  shape_data$side <- hardware_side
  
  shape_data$hardware_ <- hardware
  
  return(shape_data)
}



#' Scale the x axis of a rectangle data table
#' using the x column of tracking data
#' scale_shape fetches the width of the chambers
#' and scales the shape accodingly
#' 
#' @importFrom purrr map_dbl
#' @importFrom dplyr mutate
scale_rectangle <- function(shape_data, limits, border) {
  
  # Expand to cover the whole chamber
  shape_data$x <- purrr::map_dbl(shape_data$x,
                                 ~ifelse(
                                   sign(.) == 1, . * abs(limits[2]), ifelse(
                                     sign(.) == -1, . * abs(limits[1]), .
                                   )
                                 )
  )
  
  # Clip the decision zone
  shape_data <- shape_data %>%
    dplyr::mutate(x = dplyr::case_when(
      x == 0 ~ side * border,
      x != 0 ~ x
    ))
  
  return(shape_data)
}