# arena to use as reference for the events (odours and eshock)

#' @import data.table
#' @export
define_unique_periods <- function(lemdt_result, ref_arena=1) {
  # In order to not mix data from different blocks exhibiting the same system state
  # i.e. the period var is the same
  # we need to differentiate them
  
  # change to arena0, a proxy arena showing the state with the desired frequency
  # independent of whether the fly is tracked or not
  # right now, we have no info on the state if the arena did not find a fly
  period_map <- lemdt_result[arena==ref_arena, rle(period)]
  periods_ts <- lemdt_result[arena==ref_arena]$period
  periods_t <- lemdt_result[arena==ref_arena]$t
  
  period_first_row <- c(0,cumsum(period_map$lengths))+1
  period_first_row <- period_first_row[-length(period_first_row)]
  period_last_row <- cumsum(period_map$lengths)
  
  period_values <- unique(period_map$values)
  period_values_length <- length(unique(period_map$values))
  
  period_count <- rep(0, period_values_length)
  names(period_count) <- period_values
  
  
  for(i in 1:length(period_map$values)) {
    print(i)
    period <- period_map$values[i]
    period_count[period] <- period_count[period] + 1
    periods_ts[period_first_row[i]:period_last_row[i]] <- paste0(periods_ts[period_first_row[i]:period_last_row[i]], period_count[period])
  }
  
  periods_ts_index <- unique(data.table(t = periods_t, period = periods_ts))
  # setkey(periods_ts_index, "t")
  # time_series <- lemdt_result[,t := (round(t / freq) * freq)][, .(t, mm, pos, arena)]
  # setkey(time_series, "t")
  
  lemdt_result <- as.data.table(right_join(lemdt_result[,-"period"], periods_ts_index, by = "t"))
  return(lemdt_result)
}