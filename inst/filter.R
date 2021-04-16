#' Check no duplicates in tracker data are present
#' TODO Should be at the beginning
check_long_summary <- function(tracker_summary_long) {
  duplicate_count <- tracker_summary_long %>%
    tidyr::pivot_wider(data = ., values_from = x, names_from = region_id,
                       values_fn=length) %>%
    dplyr::select(., ROI_1:ROI_20)
  
  duplicate_pos <- which(duplicate_count != 1, arr.ind = T)
  if (dim(duplicate_pos) != c(0, 2)) {
    
    t_index <- unique(duplicate_pos[, 1])
    timepoints <- t_index[1:(min(length(t_index), 20))]
    timepoints <- tracker_summary_long[timepoints, "t"] %>% unlist
    timepoints <- paste0(timepoints, collapse = ", ")
    
    warning(
      sprintf("Some animals have more than one position for the same timepoint,
  which is impossible.
      Animals affected are: %s. I will keep only the last position.
      Timepoints affected are %s."
              , paste(paste0("ROI_", unique(duplicate_pos[,2])), collapse = ", ")
              , timepoints
      )
    )
    
    clean_summary <- tracker_summary_long %>%
      dplyr::filter(region_id == "ROI_13") %>%
      dplyr::distinct(region_id, t, .keep_all=T)
    
    return(clean_summary)
  }
  return(tracker_summary_long)
}

