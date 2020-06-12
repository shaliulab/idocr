#' @importFrom data.table setkey
process_controller_events <- function(controller_events) {
  
  # Sort the rows by the value of the timestamp
  data.table::setkey(controller_events, "t")
  # Pick the last row with the same timestamp
  controller_events <- controller_events[, .SD[.N], by = "t"]
  
  # Assign a group to each row
  # depending on which second it comes from
  controller_events[, t_round := floor(t)]
  # Pick the first row of each second where all the other data is the same
  # We need to exclude t because t is for sure not gonna be the same (just slightly off)
  x <- controller_events[, setdiff(colnames(controller_events), c("t")), with = FALSE]
  controller_events <- controller_events[!duplicated(x), ]
  
  # Finally keep only the last row from each second. We assume not more than one event
  # happens within one second
  controller_events <- controller_events[!rev(duplicated(rev(controller_events$t_round)))]
  controller_events[, t_round := NULL]
  
  return(controller_events)
}
