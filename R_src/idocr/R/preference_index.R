#' Compute the preference index of a dataset
#' 
#' The preference index is a measurement of how much
#' an animal preferes to be exposed to one stimulus
#' over another differnt stimulus or nothing.
#' If stimuli are applied on extremes of the chamber,
#' the position of the fly along the x axis of the chamber
#' can be used as proxy for preference.
#' The preference index is built upon the number of crosses
#' of a so called "decision zone" situated in the center of the chamber
#' Leaving the decision zone it in the direction of the stimulus
#' are considered evidence of preference for it, whereas
#' Leaving the decision zone on the opposite direction
#' has the opposite effect. The preference index takes the difference
#' between both and normalizes for the total number of crosses.
#' A minimum number of crosses can be required for the whole dataset
#' or for each exposure to the stimulus.
#' 
#' @param data A data.frame with two columns: type and idx
#' type encodes whether the cross is positive (preference) or negative (aversive)
#' idx encodes the exposition index. TODO Implement requirement by exposition block
#' @param min_exists_required An integer stating the minimal number
#' of cross events required for the data to be considered significant
#' @export
preference_index <- function(data, min_exits_required=5) {
  
  positive_exits <- sum(data$type == "preference")
  negative_exits <- sum(data$type == "aversive")

  numerator <- positive_exits - negative_exits
  denominator <- nrow(data)
  
  if(nrow(data) >= min_exits_required) {
    pi <- numerator / denominator
  } else {
    pi <- 0
  }
  
  return(pi)
}
