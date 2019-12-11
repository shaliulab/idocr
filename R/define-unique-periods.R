#' @import dplyr data.table
#' @export
define_unique_periods <- function(periods_dt) {
  # In order to not mix data from different blocks exhibiting the same system state
  # i.e. the period var is the same
  # we need to differentiate them
  
  # change to arena0, a proxy arena showing the state with the desired frequency
  # independent of whether the fly is tracked or not
  # right now, we have no info on the state if the arena did not find a fly
  

  period_map <- periods_dt[,rle(period)]
  periods_ts <- periods_dt$period
  periods_t <- periods_dt$t
  
  period_first_row <- c(0,cumsum(period_map$lengths))+1
  period_first_row <- period_first_row[-length(period_first_row)]
  period_last_row <- cumsum(period_map$lengths)
  
  period_values <- unique(period_map$values)
  period_values_length <- length(unique(period_map$values))
  
  period_count <- rep(0, period_values_length)
  names(period_count) <- period_values
  
  
  for(i in 1:length(period_map$values)) {
    # print(i)
    period <- period_map$values[i]
    period_count[period] <- period_count[period] + 1
    periods_ts[period_first_row[i]:period_last_row[i]] <- paste0(periods_ts[period_first_row[i]:period_last_row[i]], period_count[period])
  }
  
  periods_ts_index <- unique(data.table(t = periods_t, period_id = periods_ts))
  
  # setkey(periods_ts_index, "t")
  # time_series <- periods_dt[,t := (round(t / freq) * freq)][, .(t, mm, pos, arena)]
  # setkey(time_series, "t")
  
  periods_dt2 <- as.data.table(right_join(periods_dt, periods_ts_index, by = "t"))
  return(periods_dt2)
  
 
}
