#' @export
get_exits_dataframe <- function(lemdt_result, borders) {
  
  arena <- NULL
  
  arenas_with_data <- unique(lemdt_result$arena)
  setkeyv(lemdt_result, c('arena', 't'))
  
  
  # browser()
  result <- data.frame(x = NULL, arena = NULL, t = NULL, side = NULL)
  
    for (i in 1:length(arenas_with_data)) {
      # browser()
      lr <- lemdt_result[arena == arenas_with_data[i],]
      
      exit_time <- when_exit_happened(lr)
      result <- rbind(
        result,
        data.frame(x = borders()[[1]], arena = arenas_with_data[i], t = exit_time$left, side = "left"),
        data.frame(x = borders()[[2]], arena = arenas_with_data[i], t = exit_time$right, side = "right")
      )
    }
    
  return(result)
}

#' @export
when_exit_happened <- function(lr) {
  # lemdt_result <- as.data.table(lemdt_result)
  # lr <- lemdt_result[arena == a]
  pos <- lr$position
  # browser()
  pos_string <- paste(pos, collapse = '')
  right_rows <- gregexpr(pattern = "DR",text = pos_string)[[1]]
  left_rows <- gregexpr(pattern = "DL",text = pos_string)[[1]]
  
  suppressWarnings(if(right_rows == -1) {
    exit_right_time <- NA
  } else {
    exit_right_time <- lr[right_rows, t]
  })
  
  suppressWarnings(if(left_rows == -1) {
    exit_left_time <- NA
  } else {
    exit_left_time <- lr[left_rows, t]
  })
  
  return(list(left = exit_left_time, right = exit_right_time))
}


#' Count exits from the decision zone to either side of a chamber
#'
#' @param pos A character vector encoding the position of the fly in the chamber (L/D/R)
#' 
#' @return A list wit the number of exits from D->R (right exit), left and total (left+right)
#' @importFrom stringr str_count
#' @export
#'
#' @examples
#' pos <- c('L','L','L','D','D','D','L','L',"L",'D','D','R','R','R','D')
#' count_exits(pos)
#' 
count_exits <- function(pos) {
 
  rle_result <- rle(pos)
  rle_result$lengths
  rle_string <- paste(rle_result$values, collapse = '')
  exit_right_count <- str_count(rle_string, "DR")
  exit_left_count <- str_count(rle_string, "DL")
  total_exit_count <- (exit_right_count + exit_left_count)
  return(list(left = exit_left_count, right = exit_right_count, total = total_exit_count))
}

#' Compute the preference index of a fly for the right side,
#' as defined by PAPER
#'
#' @param pos A character vector encoding the position of the fly in the chamber (L/D/R)
#' @param min_required Number of exits required to compute the index
#' @param min_length Minimal length of the sequence of positions required to compute the index
#'
#' @return Numeric ranging 0-1 0 shows total aversion for odour on right side, and 1 total preference. -1 is return if min_required is not reached
#' @importFrom stringr str_count
#' @export
#'
#' @examples
#' pos <- c('L','L','L','D','D','D','L','L',"L",'D','D','R','R','R','D')
#' preference_index(pos)
preference_index <- function(pos=NULL, min_exits_required=5, min_length=10) {
  
  if(is.null(pos)) {
    return('preference_index')
  }
  
  if(length(pos) < min_length)
    return(NA_real_)
  
  exits <- count_exits(pos)
  exit_left <- exits[[1]]
  exit_right <- exits[[2]]
  total_exits <- exits[[3]]
  
  if(total_exits < min_exits_required)
    pi <- NA_real_
  else
    pi <- (exit_right - exit_left) / total_exits
  
  n <- count_exits(pos)[[3]]
  
  
  return(list(pi, n))
}


# #' Count how many times D is skipped on either direction
# #'
# #'
# #' @return Integer with RL and LR counts
# #' @importFrom stringr str_count
# #' @export
# #'
# count_decision_zone_is_skipped <- function(pos) {
#   
#   # returns the count of RL and LR transitions (skipping D)
#   return(c(stringr::str_count(pos, pattern = "RL"), stringr::str_count(pos, pattern = "LR")))
# }


# #' Find t when D is skipped
# #'
# #' @param t 
# #' @param pos 
# #'
# #' @return Numeric with t for each transition without D
# #' @importFrom stringr str_count
# #' @export
# #'
# find_decision_zone_non_traversed <- function(t, pos) {
#   # returns the time of all transitions skipping the decision zone
#   result <- c()
#   j <- 1
#   for(i in 1:(length(pos)-1)) {
#     if(paste(pos[i:(i+1)], collapse = '') %in% c("LR", "RL")) {
#       result[j] <- t[i] 
#       j <- j + 1
#     }
#   }
#   return(result)
# }
