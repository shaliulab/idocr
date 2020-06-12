overlap_cross_events <- function(cross_data, event_data, type="preference", mask_FUN = NULL, ...) {
  overlaps <- cross_data[NULL,]
  
  if (type == "preference") {
    operator <- `==`
  } else if(type == "aversive") {
    operator <- `!=`
  } else {
    stop("Please pass a valid type. Either 'preference' or 'aversive'")
  }
  
  cross_data <- mask_FUN(cross_data, ...)
  
  for(i in 1:nrow(cross_data)) {
    row <- cross_data[i,]
    event_hits <- (row[["t"]] * 1000) > event_data$t_start & (row[["t"]] * 1000) < event_data$t_end & operator(row[["side"]], event_data$side)
    if( sum(event_hits) > 0 ) {
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
