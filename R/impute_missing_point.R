#' @import data.table zoo
#' @export
impute_missing_point <- function(lemdt_result) {
  
  lemdt_result[, imputed := FALSE]
  
  lemdt_result[is.na(mm_mean), imputed :=  TRUE]
  
  mm_mean_imputed <- numeric()
  period_imputed <- character()
  
  available_arenas <- unique(lemdt_result$arena)
  
  for(arena_id in available_arenas) {
    ts_subset <- lemdt_result[arena == arena_id]
    mm_mean_imputed <- c(mm_mean_imputed, approxfun(
      x = 1:nrow(ts_subset),
      y = ts_subset$mm_mean,
      method = "linear")(1:nrow(ts_subset))
    )
   
    # period_imputed <- c(
      # period_imputed,
      
    #   na.locf(na.locf(zoo(ts_subset$period), na.rm=FALSE), fromLast=TRUE)
    #   )
    
    
    
  }
  
  period_imputed <- rep(lemdt_result[arena==0, period], times = 21)
  period_id_imputed <- rep(lemdt_result[arena==0, period_id], times = 21)
  lemdt_result <- as.data.table(arrange(lemdt_result, by = arena))
  lemdt_result[, mm_mean := mm_mean_imputed]
  lemdt_result[, period := period_imputed]
  lemdt_result[, period_id := period_id_imputed]
  return(lemdt_result)
  
}
