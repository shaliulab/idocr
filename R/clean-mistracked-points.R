# maximum number of pixels between 2 positions contiguous in time
# that the fly can traverse. If greater, the fly was mistracked

#' @importFrom data.table data.table :=
#' @export
clean_mistracked_points <- function(lemdt_result, threshold=10) {
  
  arena <- to_clean <- arena_id <- mm_mean <- NULL
  
 # lemdt_result <- lemdt_result2
 lemdt_result$to_clean <- FALSE
  for (arena_id in 1:20) {
    print(arena_id)
    tryCatch({
    if(lemdt_result[arena == arena_id, all(is.na(mm_mean))]) {
      lemdt_result[(lemdt_result$arena == arena_id), "to_clean"] <- TRUE
      next()
    }
    
    lemdt_result[
      which(lemdt_result$arena == arena_id)[
        unique(c(which(diff(lemdt_result[arena == arena_id]$mm_mean) > + threshold)+1,
                 which(diff(lemdt_result[arena == arena_id]$mm_mean) < - threshold)))
        ], mm_mean := NA
      ]
    }, error = function(e) {browser()})
    
  }
 
 lemdt_result <- as.data.table(lemdt_result)[!lemdt_result$to_clean,]
 lemdt_result[,to_clean := NULL]

  return(lemdt_result)
}