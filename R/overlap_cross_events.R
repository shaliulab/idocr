#'
#'  @export
overlap_cross_events <- function(cross_data, event_data, type="preference", mask_FUN = NULL, mirror=FALSE, ...) {
  overlaps <- cross_data[NULL,]
 
  if (mirror) { 
    if (type == "preference") {
      operator <- `==`
    } else if(type == "aversive") {
      operator <- `!=`
    } else {
      stop("Please pass a valid type. Either 'preference' or 'aversive'")
    }
  } else {
    operator <- `==`
  }
  
  # cross_data <- mask_FUN(cross_data, ...)
  
  for(i in 1:nrow(cross_data)) {
    row <- cross_data[i,]
    event_hits <- (row[["t"]] * 1000) > event_data$t_start & (row[["t"]] * 1000) < event_data$t_end & operator(row[["side"]], event_data$side)
    if( sum(event_hits) == 1) {
      row$idx <- event_data[event_hits,]$idx
      overlaps <- rbind(overlaps, row)
    }
  }
  return(overlaps)
}

#' Dont count crosses happening within less than seconds_masked seconds
#' since the previous one
seconds_mask <- function(data, seconds_masked = 5) {
  data$dt <- c(Inf, diff(data$t))
  mask <- data[data$dt > seconds_masked,]
  return(mask)
}

#' Wrapper around overlap_cross_events for both apetitive and aversive behavior
compute_preference_data <-function(cross_data, event_data, CSplus, CSminus) {
  # TODO Beyond should be TRUE when the cross is outside of the decision zone
  # However, it is opposite
  apetitive <- overlap_cross_events(
    cross_data[cross_data$beyond,],
    event_data[event_data$hardware_small == CSplus,],
    type = "apetitive", mask_FUN = seconds_mask
  )
  
  aversive <- overlap_cross_events(
    cross_data[cross_data$beyond,],
    event_data[event_data$hardware_small == CSminus,],
    type = "aversive", mask_FUN = seconds_mask
  )
  
  preference_data <- rbind(
    cbind(
      apetitive,
      type = "apetitive"
    ),
    cbind(
      aversive,
      type = "aversive"
    )
  )
  
  return(preference_data)
  
}
