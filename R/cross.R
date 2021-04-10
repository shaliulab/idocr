#' Annotate registered corsses with either appetitive or aversive behavior
#'
#' @param cross_data dataframe where each row is an exit, defined by region_id, t and side
#' @param event_data dataframe where each row is an event, defined by stimulus, t_start t_end, side
#' @return 
annotate_cross <- function(cross_data, event_data, treatment, type="appetitive") {
  
  event_data <- event_data[event_data$treatment == treatment,]

  overlaps <- cross_data[NULL,]

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


#' Ignore too close crosses
#' 
#' Dont count crosses happening within less than seconds_masked seconds
#' since the previous one
#' @param cross_data Dataset of crosses
#' @param min_time Minimum amount of seconds between crosses allowed
#' @importFrom dplyr mutate nest_by arrange lag
#' @importFrom tidyr unnest
seconds_mask <- function(cross_data, min_time = 0) {

  original_order <- colnames(cross_data)
  
  if ("dt" %in% colnames(cross_data)) {
    cross_data$dt <- NULL
    warning(
    "seconds_mask has received a dataset with an existing dt column
     Did seconds_mask already run in this dataset?
     seconds_mask will overwrite the existing dt column
    ")
  }
  
  cross_data_dt <- cross_data %>%
    dplyr::arrange(region_id, t) %>%
    dplyr::nest_by(region_id) %>%
    # by choosing this default, the first dt is always equal to duration (x - (x - duration) = duration)
    # this way the first exit is never discarded
    dplyr::mutate(dt = list(data$t - dplyr::lag(data$t, n=1, default = data$t[1] - min_time))) %>%
    tidyr::unnest(cols = c(data, dt)) %>%
    dplyr::ungroup()
  
  # TODO Can we actually to remove dt once we filter based on it (on following line)
  # or do we need it later?
  masked <- cross_data_dt[cross_data_dt$dt >= min_time, c(original_order, "dt")]
  return(masked)
}

#' Detect crosses of the decision zone
#' 
#' Report timepoints when the animal crossed on either direction
#' (in/out) the decision zone on the passed `side`.
#' The decision zone is `border` pixels far from the center
#' @param tracker_data
#' @eval document_border()
#' @param side Either LEFT (-1) or RIGHT (1)
#' @importFrom tibble tibble
#' @export
cross_detector <- function(tracker_data, border, side=c(-1, 1)) {
  
  length_encoding <- rle((tracker_data$x * side) > border)
  
  cross_data <- tibble::tibble(
    lengths = length_encoding$lengths,
    out_of_zone = length_encoding$values,
    index = cumsum(length_encoding$lengths)
  )
  
  cross_data$t <- tracker_data[cross_data$index, ]$t
  cross_data <- cross_data[, c("t", "out_of_zone")]
  cross_data$border <- border
  cross_data$side <- side
  cross_data$in_zone <- !cross_data$out_of_zone
  return(cross_data)
}

#' TODO Write documentation!
#' @param tracker_data
#' @param border Distance in pixels from center to decision zone edge
#' @param side Integer either -1 (left) or 1 (right)
#' @param cross_detector_FUN Cross detector function
#' @param mask_FUN Masking function to ignore certain crosses given some heuristic
#' @importFrom purrr map
#' @importFrom tibble as_tibble
#' @importFrom dplyr filter
#' @importFrom magrittr `%>%`
#' @seealso seconds_mask
#' @seealso cross_detector
#' @export
find_exits <- function(tracker_data, border, side=c(-1, 1),
                       cross_detector_FUN = cross_detector,
                       mask_FUN = seconds_mask,
                       ...) {
  
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
        region_id = unique(tracker_data[tracker_data$id == .,]$region_id),
        tracker_data[tracker_data$id == ., ] %>% cross_detector_FUN(., border = border, side = side)
      )
    ) %>%
    lapply(., function(x) mask_FUN(x, ...)) %>%
    do.call(rbind, .) %>%
    dplyr::filter(out_of_zone) %>%
    tibble::as_tibble(.)
  
  cross_data$x <- cross_data$border * cross_data$side
  
  return(cross_data)
}

#' Wrapper around find_exit_decisions for left and right
#' @param ... Extra arguments to find_exits
#' @seealso find_exits
find_exits_all <- function(...) {
  cross_data <- rbind(
    find_exits(side = -1, ...),
    find_exits(side = 1, ...)
  )
  
  return(cross_data)
}

#' Wrapper around annotate_cross for appetitive and aversive conditioning
#' @param cross_data
#' @param event_data
#' @param CSplus
#' @param CSminus
annotate_cross_all <- function(cross_data, event_data, CSplus, CSminus) {
  rbind(
    annotate_cross(cross_data, event_data, CSplus, "appetitive"),
    annotate_cross(cross_data, event_data, CSminus, "aversive")
  )
}
