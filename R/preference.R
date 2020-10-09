#' Wrapper around overlap_cross_events for both apetitive and aversive behavior
#' @param cross_data A dataframe with one row per exit (cross)
#' @param rectangle_data A list of dataframes containing one rectangle each
#' @param CSplus Name of the hardware associated to the apetitive stimulus
#' @param CSminus Name of the hardware associated to the aversive stimulus
compute_preference_data <- function(cross_data, rectangle_data, CSplus, CSminus, mask_duration=0.5) {
  # TODO Beyond should be TRUE when the cross is outside of the decision zone
  # However, it is opposite
  
  event_data <- lapply(rectangle_data, reshape_controller) %>% do.call(rbind, .)
  
  apetitive <- overlap_cross_events(
    cross_data[cross_data$beyond,],
    event_data[event_data$hardware_small == CSplus,],
    type = "apetitive", mask_FUN = seconds_mask, duration = mask_duration
  )
  
  aversive <- overlap_cross_events(
    cross_data[cross_data$beyond,],
    event_data[event_data$hardware_small == CSminus,],
    type = "aversive", mask_FUN = seconds_mask, duration = mask_duration
  )
  
  apetitive$type <- "apetitive"
  aversive$type <- "aversive"

  preference_data <- rbind(cbind(apetitive), cbind(aversive))
  
  return(preference_data)
  
}

#' @importFrom tidyr pivot_wider
#' @importFrom dplyr nest_by summarise group_by ungroup full_join
compute_pi_data <- function(preference_data, min_exits_required = 5) {
  # Compute the preference index based on region-id indexed data
  
  pi_data <- preference_data %>%
    dplyr::group_by(region_id, type) %>%
    dplyr::summarise(count = n()) %>%
    tidyr::pivot_wider(id_cols = "region_id",
                       names_from = "type",
                       values_from = "count")
  
  na <- FALSE
  if(! "apetitive" %in% colnames(pi_data)) pi_data$apetitive <- 0; na <- TRUE
  if(! "aversive" %in% colnames(pi_data)) pi_data$aversive <- 0; na <- TRUE
    
  
  # pi_data[, c('apetitive', 'aversive')][is.na(pi_data[, c('apetitive', 'aversive')])] <- 0
  
  pi_data_summ <- pi_data %>%
    dplyr::ungroup() %>%
    dplyr::nest_by(region_id) %>%
    dplyr::summarise(preference_index = preference_index(data$apetitive, data$aversive, min_exits_required = min_exits_required)) %>%
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
#' @param apetitive Number of exits towards the CSplus simulus
#' @param aversive Number of exits towards the CSminus stimulus
#' @param min_exists_required An integer stating the minimal number
#' of cross events required for the data to be considered significant
#' @export
preference_index <- function(apetitive, aversive, min_exits_required=5) {
  
  # positive_exits <- sum(data$type == "preference")
  # negative_exits <- sum(data$type == "aversive")
  
  numerator <- apetitive - aversive
  denominator <- apetitive + aversive
  
  
  if (denominator >= min_exits_required) {
    pi <- numerator / denominator
  } else {
    pi <- 0
  }
  
  return(pi)
}

