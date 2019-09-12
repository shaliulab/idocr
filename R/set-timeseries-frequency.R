# time series frequency (s)
# bin the data in windows of size freq
# datapoints in the same window are averaged
#' @importFrom data.table data.table
#' @import magrittr
#' @importFrom dplyr full_join arrange rename summarise group_by
#' @export
set_timeseries_frequency <- function(lemdt_result, freq=.25, ref_arena=1){
  time_index <- seq(0, max(lemdt_result$t), freq)
  reference_time <- data.table(t = rep(time_index, times = 20), arena = rep(1:20, each = length(time_index)))
  periods_t <- lemdt_result[arena == ref_arena, round(t / freq) * freq]
  
  print(colnames(lemdt_result))
  
  lemdt_result <- lemdt_result[,.(t_round = round(t/ freq) * freq, arena, t, mm, period)] %>%
    group_by(arena, t_round, period) %>%
    summarise(
      # pos_mode = names(sort(table(pos), decreasing = T))[1],
      mm_mean = mean(mm),
    ) %>%
    arrange(arena, t_round) %>%
    rename(t = t_round) %>%
    as.data.table
  
  
  lemdt_result <- as.data.table(full_join(reference_time, lemdt_result))
  return(lemdt_result)
}
