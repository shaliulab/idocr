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
