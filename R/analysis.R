#' Analyse an IDOC dataset
#' 
#' Take an IDOC dataset
#' @eval document_dataset()
#' @param min_exits_required Minimal number of exits
#' to be considered for significance
#' @param ... Extra arguments to find_exits_all
#' @seealso [annotate_cross()]
analyse_dataset <- function(dataset, min_exits_required=5, ...) {
  
  tracker_data <- dataset$tracker
  controller_data <- dataset$controller
  
  # get controller information
  message("Preparing controller data")
  rectangle_data <- define_rectangle_all(dataset)
  event_data <- get_event_data(dataset)

  # get cross information by inferring
  # crosses based on tracker data and predefined borders
  message("Detecting decision zone exits i.e. crosses")
  cross_data <- find_exits_all(
    tracker_data = tracker_data,
    border = dataset$border,
    ...
  )
  stopifnot(nrow(cross_data) > 0)
  
  # one row per exit
  message("Assigning sign to exits (appetitive or aversive)")
  annotated_data <- annotate_cross_all(
    cross_data, event_data,
    dataset$CSplus, dataset$CSminus
  )

  # one row per fly with count of appetitive and aversive exits
  # as well as the computed preference index
  message("Computing channel-wise preference index")
  if (nrow(annotated_data) == 0) {
    warning("No decision zone crosses detected. I will skip PI computation")
    pi_data <- NA
  } else {
    pi_data <- compute_preference_index(
      annotated_data,
      min_exits_required = min_exits_required
    )
  }
  
  return(list(
    annotation = annotated_data,
    pi = pi_data,
    rectangles = rectangle_data
  ))
}
