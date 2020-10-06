
#' @param cross_data dataframe where each row is an exit, defined by region_id, t and side
#' @param event_data dataframe where each row is an event, defined by hardware_, t_start t_end, side and hardware_small
overlap_cross_events <- function(cross_data, event_data, type="apetitive", mask_FUN = NULL, mirror=FALSE, ...) {
  overlaps <- cross_data[NULL,]
  
  if (mirror) { 
    if (type == "apetitive") {
      operator <- `==`
    } else if (type == "aversive") {
      operator <- `!=`
    } else {
      stop("Please pass a valid type. Either 'apetitive' or 'aversive'")
    }
  } else {
    operator <- `==`
  }
  
  cross_data <- mask_FUN(cross_data, ...)
  
  for (i in 1:nrow(cross_data)) {
    row <- cross_data[i,]
    event_hits <- (row[["t"]] * 1000) > event_data$t_start & (row[["t"]] * 1000) < event_data$t_end & operator(row[["side"]], event_data$side)
    if (sum(event_hits) == 1) {
      row$idx <- event_data[event_hits,]$idx
      overlaps <- rbind(overlaps, row)
    }
  }
  return(overlaps)
}

#' Parse side from the hardware name
#' 
#' Return -1 for left and 1 for right
#'
#' @importFrom stringr str_match
#' @importFrom purrr map_chr map
#' @import magrittr
parse_side <- function(hardware) {
  hardware_side <- purrr::map(hardware, 
                              ~c(
                                stringr::str_match(pattern = "RIGHT", string = .)[, 1],
                                stringr::str_match(pattern = "LEFT", string = .)[, 1]
                              )
  ) %>%
    purrr::map_chr(~na.omit(unlist(.)))
  
  mapping <- c("LEFT" = -1, "RIGHT" = 1)
  hardware_side <- mapping[hardware_side]
  
  return(hardware_side)
}


#' Reshape controller data to a format where it is
#' easy to merge with cross_data
#' 
#' Enter a dataframe with one row per corner
#' get a new dataframe with one row per event (1/4 of the rows)
#' @import magrittr 
#' @importFrom dplyr group_by summarise
#' @export
reshape_controller <- function(rectangle_data) {
  
  # rectangle_data$side <- parse_side(rectangle_data$hardware_)
  
  event_data <- rectangle_data %>% group_by(hardware_, group) %>%
    summarise(t_start = min(t_ms), t_end = max(t_ms), side = unique(side)) %>%
    mutate(idx = group) %>% select(-group)
  
  event_data$hardware_small <- unlist(lapply(
    strsplit(event_data$hardware_, split = "_"),
    function(x) {
      paste(x[1:2], collapse = "_")
    }))
  
  return(event_data)
}


#' Dont count crosses happening within less than seconds_masked seconds
#' since the previous one
seconds_mask <- function(data, duration = 0) {
  data$dt <- c(Inf, diff(data$t))
  mask <- data[data$dt > duration,]
  return(mask)
}


#' @importFrom tibble tibble
#' @export
cross_detector <- function(roi_data, border, side=1) {
  
  length_encoding <- rle((roi_data$x * side) > border)
  
  cross_data <- tibble(
    lengths = length_encoding$lengths,
    beyond = length_encoding$values,
    index = cumsum(length_encoding$lengths)
  )
  
  cross_data$t <- roi_data[cross_data$index, ]$t
  cross_data <- cross_data[, c("t", "beyond")]
  cross_data$border <- border
  cross_data$side <- side
  cross_data$beyond <- !cross_data$beyond
  
  return(cross_data)
}


# TODO
# Make this a test
# is_cross(roi_data[roi_data$region_id == 10, ], border = 10, side = 1)

#' @importFrom purrr map
#' @importFrom tibble as_tibble
#' @import magrittr
#' @export
gather_cross_data <- function(cross_detector_FUN = cross_detector, roi_data, border, side) {
  
  # browser()
  
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

#' Wrapper around gather_cross_data for left and right
infer_decision_zone_exits <- function(roi_data,  border=border, cross_detector_FUN=cross_detector) {
  cross_data <- rbind(
    gather_cross_data(cross_detector_FUN = cross_detector, roi_data, border = border, side = 1),
    gather_cross_data(cross_detector_FUN = cross_detector, roi_data, border = border, side = -1)
  )
  return(cross_data)
}
