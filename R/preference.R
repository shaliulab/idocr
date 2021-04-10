#' Compute the preference index displayed by the animals in a dataset
#' @param annotated_data
#' @param min_exits_required Minimum number of exists required
#' when computing the preference index. Animals not reaching this number of exits
#' are not considered in the analysis
#' @importFrom dplyr nest_by summarise group_by ungroup full_join n
#' @importFrom tidyr pivot_wider
#' @importFrom magrittr `%>%`
compute_preference_index <- function(annotated_data, min_exits_required = 5) {
  # Compute the preference index based on region-id indexed data

  pi_data <- annotated_data %>%
    dplyr::group_by(region_id, type) %>%
    dplyr::summarise(count = dplyr::n()) %>%
    tidyr::pivot_wider(
      id_cols = "region_id",
      names_from = "type",
      values_from = "count"
    )
  
  na <- FALSE
  if(! "appetitive" %in% colnames(pi_data)) {pi_data$appetitive <- 0; na <- TRUE}
  if(! "aversive" %in% colnames(pi_data)) {pi_data$aversive <- 0; na <- TRUE}
    
  pi_data[is.na(pi_data$appetitive), "appetitive"] <- 0
  pi_data[is.na(pi_data$aversive), "aversive"] <- 0
  
  # pi_data[, c('appetitive', 'aversive')][is.na(pi_data[, c('appetitive', 'aversive')])] <- 0
  
  pi_data_summ <- pi_data %>%
    dplyr::ungroup() %>%
    dplyr::nest_by(region_id) %>%
    dplyr::summarise(preference_index = preference_index(data$appetitive, data$aversive, min_exits_required = min_exits_required)) %>%
    dplyr::ungroup()
  
  # na should be 0 in this case
  pi_data <- dplyr::full_join(pi_data, pi_data_summ)
  
  if(na) pi_data$preference_index <- "NA"
  
  return(pi_data)
}


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
#' @param appetitive Number of exits towards the CSplus simulus
#' @param aversive Number of exits towards the CSminus stimulus
#' @param min_exists_required An integer stating the minimal number
#' of cross events required for the data to be considered significant
#' @export
preference_index <- function(appetitive, aversive, min_exits_required=5) {
  
  numerator <- appetitive - aversive
  denominator <- appetitive + aversive
  
  if (denominator >= min_exits_required) {
    pi <- numerator / denominator
  } else {
    pi <- NA
  }
  
  return(pi)
}