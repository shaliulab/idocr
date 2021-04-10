#' Analyse an IDOC dataset
#' 
#' Take an IDOC dataset
#' @eva document_dataset()
#' @inherit compute_preference_index
#' @param ... Additional arguments to annotate_cross
#' @seealso annotate_cross
#' @seealso annotate_cross
analyse_dataset <- function(dataset, min_exits_required, min_time=0, ...) {
  
  tracker_data <- dataset$tracker
  controller_data <- dataset$controller
  
  # get controller information
  message("Preparing controller data")
  rectangle_data <- define_rectangles(dataset)
  event_data <- get_event_data(dataset)

  # get cross information by inferring
  # crosses based on tracking data and predefined borders
  message("Detecting decision zone exits i.e. crosses")
  cross_data <- find_exits_all(
    tracker_data = tracker_data,
    border = dataset$border, min_time = min_time
  )

  # one row per exit
  message("Assigning sign to exits (appetitive or aversive)")
  annotated_data <- annotate_cross_all(
    cross_data, event_data,
    dataset$CSplus, dataset$CSminus
  )

  # one row per fly with count of appetitive and aversive exits
  # as well as the computed preference index
  message("Computing channel-wise preference index")
  pi_data <- compute_preference_index(
    annotated_data,
    min_exits_required = min_exits_required
  )
  
  return(list(
    annotation = annotated_data,
    pi = pi_data,
    rectangles = rectangle_data
  ))
}
