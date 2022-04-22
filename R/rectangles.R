#' Wrapper around define_rectangle for several stimulus
#' 
#' @eval document_dataset() 
#' @importFrom purrr map
#' @importFrom dplyr mutate group_by group_split
#' @importFrom magrittr `%>%`
define_rectangle_all <- function(dataset) {
  
  . <- stimulus <- NULL
  
  stopifnot(!is.null(dataset$controller))
  stopifnot(!is.null(dataset$stimuli))
  stopifnot(!is.null(dataset$limits))
  
  controller_data <- dataset$controller
  rect_pad <- 0

  ## Reformat the wide table
  ### We get one row for every corner of the rectangles shown on the plot
  ### to represent when the stimulus items listed in `stimulus`
  ### are on
  ### The row states:
  ### * x -> the position (-1,0,1) of the corner
  ### * side -> the side where the rectangle is (-1 if on the left and 1 if on the right)
  ### * stimulus -> name of the stimulus item
  ### * t_ms -> time in milliseconds

  controller_data <- purrr::map(
    dataset$stimuli,
    function(x) {
      define_rectangle(
        controller_data = controller_data,
        stimulus = x
      )
    }) %>%
    do.call(rbind, .) %>%
    dplyr::mutate(t_ms = t * 1000)
  
  controller_data$treatment <- unlist(lapply(
    controller_data$stimulus, remove_side
  ))
  
  rectangle_data <- controller_data %>%
    dplyr::group_by(stimulus) %>%
    dplyr::group_split() %>%
    purrr::map(~scale_rectangle(., dataset$limits, rect_pad))
  
  return(rectangle_data)
}


#' Reshape the controller data to be plotted in ggplot2
#'
#' Given a table containing when several stimulus turned on/off
#' during an experiment, and a piece of stimulus,
#' prepare_shape_data will generate a table with one row per corner in a rectangle
#' encompassing all the area of the plot where the stimulus is active
#' This is given by its side (X axis) and the time when it was on (Y axis)
#' If the stimulus was turned on/off n times, we get n rectangles and thus n*4 rows.#' 
#' The x axis is assumed to go from -1 to 1. To scale it, see scale_shape
#' @eval document_controller_data()
#' @eval document_stimulus()
#' @importFrom magrittr `%>%`
#' @import data.table
#' @export
define_rectangle <- function(controller_data, stimulus) {
  
  # Detect side of stimulus
  stimulus_side <- parse_side(stimulus)
  x_values <- list("-1" = c(-1, 0), "1" = c(0, 1))
  x_vals <- x_values[[as.character(stimulus_side)]]
  
  # keep just time and the column for the current stimulus
  controller_data <- controller_data[, c("t", stimulus), with = F]
  # remove possible dups
  controller_data <- controller_data[!duplicated(controller_data), ]
  switches <- validate_events(controller_data, stimulus)
  
  # we are making rectangles, so generate 2 extra points
  # for each pair of on-off events
  shape_data <- data.table(
    x = rep(rep(x_vals, times = 2), length(switches) / 2),
    t = rep(round(switches), each = 2)
  )
  
  # assign the blocks of 4 points to  single group (shape)
  shape_data$group <- 0:(nrow(shape_data) - 1) %/% 4
  
  # sort the block as expected by geom_polygon
  setkey(shape_data, "group")
  shape_data <- shape_data[, .SD[c(1, 2, 4, 3)], by = "group"]
  shape_data$side <- stimulus_side
  shape_data$stimulus <- stimulus
  return(shape_data)
}

#' Given a dataset, find the timepoints
#' where the stimulus changes state
#' @eval document_controller_data()
#' @eval document_stimulus() 
validate_events <- function(controller_data, stimulus) {
  
  . <- NULL
  
  stimulus_events <- controller_data[[stimulus]] %>%
    # detect differences
    diff %>%
    # add something at the beginning
    # to align the differences with the original time series
    # a 0 means no change (which makes sense because it is t0)
    c(0, .)
  
  # the order with which 
  # we diff and then add the 0
  # does NOT matter
  if (sum(stimulus_events) != 0) {
    stop(sprintf("Problem parsing an end timestamp for %s", stimulus))
  }
  
  # Pick the time at which this differences occur
  switches <- controller_data[which(as.logical(abs(stimulus_events))), t]
  
  if (length(switches) %% 2 != 0) {
    stop(sprintf("Problem parsing an end timestamp for %s", stimulus))
  }
  return(switches)
}



#' Scale the x axis of a rectangle data table
#' using the x column of tracker data
#' scale_shape fetches the width of the chambers
#' and scales the shape accodingly
#' 
#' @eval document_shape_data()
#' @eval document_limits()
#' @eval document_border()
#' @importFrom purrr map_dbl
#' @importFrom dplyr mutate case_when
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