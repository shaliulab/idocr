# Time series frequency (s)
#
# Bin the data in windows of size freq
# The datapoints in the same window are averaged
#' @importFrom data.table data.table
#' @import magrittr
#' @importFrom dplyr full_join arrange rename summarise group_by
#' @export
set_timeseries_frequency <- function(self, freq=.25) {
  
  lemdt_result <- self$lemdt_result
  lemdt_result <- lemdt_result[, t_round := floor(t/ freq) * freq]
  
  
  n_arenas <- length(self$selected_flies) + 1
  
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
      arena = rep(c(0, self$selected_flies), each = length(time_index))
    # ),
    
  )
  
  # summarise the data so there is one datapoint every freq seconds
  # still not all timepoints are present because for some intervals there is no data 
  # only works if lemdt_result is a data.table
  if (!("data.table" %in% class(lemdt_result))) stop("lemdt_result is not a data.table. Ensure it is!")
    
  # create a column called t_round that will have the same value for all datapoints to be summarised into a single one
  # this t_round will be the lowest value of t in each group of datapoints

  # summarise using this t_round column (also by arena)
  lemdt_result <- lemdt_result[, .(mm_mean = mean(mm), period = names(table(period))[1]), by = .(arena, t_round)]
  setnames(lemdt_result, "t_round", "t")
  lemdt_result <- define_unique_periods(lemdt_result)
  

  # merge the template and the data
  lemdt_result <- merge(reference_dt, lemdt_result, by = c('t', 'arena'), all = T)
  
  return(lemdt_result)
}
