#' Annotate registered corsses with either appetitive or aversive behavior
#'
#' @param cross_data dataframe where each row is an exit, defined by region_id, t and side
#' @param event_data dataframe where each row is an event, defined by stimulus, t_start t_end, side
#' @return 
annotate_cross <- function(cross_data, event_data, treatment, type="appetitive", mask_FUN = seconds_mask, ...) {
  
  cross_data <- cross_data[cross_data$beyond,]
  event_data <- event_data[event_data$treatment == treatment,]

  overlaps <- cross_data[NULL,]
  cross_data <- mask_FUN(cross_data, ...)

  for (i in 1:nrow(cross_data)) {
    row <- cross_data[i,]
    t_ms <- row[["t"]] * 1000
    event_hits <- t_ms > event_data$t_start & t_ms < event_data$t_end & row[["side"]] == event_data$side
    if (sum(event_hits) == 1) {
      row$idx <- event_data[event_hits,]$idx
      overlaps <- rbind(overlaps, row)
    }
  }
  
  overlaps$type <- type
  
  return(overlaps)
}

#' Parse side from the hardware name
#' 
#' Return -1 for left and 1 for right
#'
#' @importFrom stringr str_match
#' @importFrom purrr map_chr map
#' @importFrom magrittr `%>%`
#' @param stimulus Name of stimulus to be parsed
parse_side <- function(stimulus) {
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


#' Reshape controller data to a format where it is
#' easy to merge with cross_data
#' 
#' Enter a dataframe with one row per corner
#' get a new dataframe with one row per event (1/4 of the rows)
#' @importFrom magrittr `%>%` 
#' @importFrom dplyr group_by summarise select mutate
#' @export
reshape_controller <- function(rectangle_data) {
  
  event_data <- rectangle_data %>% dplyr::group_by(stimulus, group) %>%
    dplyr::summarise(t_start = min(t_ms), t_end = max(t_ms), side = unique(side)) %>%
    dplyr::mutate(idx = group) %>% dplyr::select(-group)
  
  event_data$treatment <- unlist(lapply(
    strsplit(event_data$stimulus, split = "_"),
    function(x) {
      paste(x[1:2], collapse = "_")
    }))
  
  return(event_data)
}


#' Ignore too close crosses
#' 
#' Dont count crosses happening within less than seconds_masked seconds
#' since the previous one
#' @param cross_data Dataset of crosses
#' @param min_time Minimum amount of seconds between crosses allowed
#' @importFrom dplyr mutate nest_by arrange
#' @importFrom tidyr unnest
seconds_mask <- function(cross_data, min_time = 0) {

  # browser()
  original_order <- colnames(cross_data)
  
  cross_data_dt <- cross_data %>%
    dplyr::arrange(region_id, t) %>%
    dplyr::nest_by(region_id) %>%
    # by choosing this default, the first dt is always equal to duration (x - (x - duration) = duration)
    # this way the first exit is never discarded
    dplyr::mutate(dt = list(data$t - lag(data$t, default = data$t[1] - min_time))) %>%
    tidyr::unnest(cols = c(data, dt)) %>%
    dplyr::ungroup()
  
  # TODO Can we actually to remove dt once we filter based on it (on following line)
  # or do we need it later?
  mask <- cross_data_dt[cross_data_dt$dt >= min_time, c(original_order, "dt")]
  return(mask)
}


#' @importFrom tibble tibble
#' @export
cross_detector <- function(tracker_data, border, side=1) {
  
  length_encoding <- rle((tracker_data$x * side) > border)
  
  cross_data <- tibble(
    lengths = length_encoding$lengths,
    beyond = length_encoding$values,
    index = cumsum(length_encoding$lengths)
  )
  
  cross_data$t <- tracker_data[cross_data$index, ]$t
  cross_data <- cross_data[, c("t", "beyond")]
  cross_data$border <- border
  cross_data$side <- side
  cross_data$beyond <- !cross_data$beyond
  return(cross_data)
}


# TODO
# Make this a test
# is_cross(tracker_data[tracker_data$region_id == 10, ], border = 10, side = 1)

#' @importFrom purrr map
#' @importFrom tibble as_tibble
#' @importFrom magrittr `%>%`
#' @export
find_exits <- function(tracker_data, border, side, cross_detector_FUN = cross_detector) {
  
  cross_data <- tracker_data %>%
    # get a clean of populated ids
    clean_empty_roi(.) %>%
    select(id) %>%
    unique %>%
    unlist %>%
    # .[1:2] %>%
    # for each of them create a new data.table
    purrr::map(
      ~cbind(
        id = .,
        region_id = unique(tracker_data[tracker_data$id == ., "region_id"]),
        tracker_data[tracker_data$id == ., ] %>% cross_detector_FUN(., border = border, side = side)
      )
    ) %>%
    do.call(rbind, .) %>%
    as_tibble
  
  cross_data$x <- cross_data$border * cross_data$side
  return(cross_data)
}

#' Wrapper around find_exit_decisions for left and right
find_exits_all <- function(...) {
  cross_data <- rbind(
    find_exits(side = 1, ...),
    find_exits(side = -1, ...)
  )
  return(cross_data)
}
