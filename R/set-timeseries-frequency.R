# time series frequency (s)
# bin the data in windows of size freq
# datapoints in the same window are averaged
#' @importFrom data.table data.table
#' @import magrittr
#' @importFrom dplyr full_join arrange rename summarise group_by
#' @export
set_timeseries_frequency <- function(lemdt_result, freq=.25) {
  
  n_arenas <- length(unique(lemdt_result$arena))
  
  
  # the timepoints for which we will have a datapoint
  time_index <- seq(0, max(lemdt_result$t), freq)
  
  # a template for the final dt
  # where every arena has the 
  # same number of datapoints
  # and its equal to the length of time_index
  reference_dt <- data.table(
    # t_arena = paste0(
      t = rep(time_index, times = n_arenas),
      # '_',
      arena = rep(0:20, each = length(time_index))
    # ),
    
  ) 
  
  # summarise the data so there is one datapoint every freq seconds
  # still not all timepoints are present because for some intervals there is no data 
  lemdt_result <- lemdt_result[, t_round := floor(t/ freq) * freq]
    
  lemdt_result <- lemdt_result %>% group_by(arena, t_round) %>%
    summarise(
      # pos_mode = names(sort(table(pos), decreasing = T))[1],
      mm_mean = mean(mm),
    ) %>%
    arrange(arena, t_round) %>%
    rename(t = t_round) %>%
    as.data.table
  
  # table(lemdt_result$arena)
  
  lemdt_result[, t_arena := paste0(t, '_', arena)]
  reference_dt[, t_arena := paste0(t, '_', arena)]
  
  
  lemdt_result <- merge(reference_dt, lemdt_result, by = c('t', 'arena'), all = T)
  # table(lemdt_result$arena)
  
  lemdt_result[arena == 20, t[duplicated(t)]]
  lemdt_result[arena == 20 & t == 300.75 ]
  
  lemdt_result <- as.data.table(lemdt_result)
  lemdt_result[, t_arena.x := NULL]
  lemdt_result[, t_arena.y := NULL]
  
  return(lemdt_result)
}
