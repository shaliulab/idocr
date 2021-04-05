analyse_dataset <- function(dataset, min_exits_required, ...) {
  
  tracker_data <- dataset$tracker
  controller_data <- dataset$controller
  
  # get controller information
  message("Preparing controller data")
  rectangle_data <- define_rectangles(dataset)
  event_data <- get_event_data(dataset)

  # get cross information by inferring
  # crosses based on tracking data and predefined borders
  message("Detecting decision zone exits")
  cross_data <- find_exits_all(tracker_data=tracker_data, border = dataset$border)

  # one row per exit
  message("Assigning sign to exits (appetitive or aversive or neutral")
  annotated_data <- rbind(
    annotate_cross(cross_data, event_data, dataset$CSplus, "appetitive", ...),
    annotate_cross(cross_data, event_data, dataset$CSminus, "aversive", ...)
  )
  
  # one row per fly with count of appetitive and aversive exits
  # as well as the computed preference index
  message("Computing channel-wise preference index")
  pi_data <- compute_preference_index(annotated_data, min_exits_required = min_exits_required)
  
  return(list(annotation=annotated_data, pi=pi_data, rectangles=rectangle_data))
}
