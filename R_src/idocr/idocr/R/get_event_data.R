#' Reshape controller data to a format where it is
#' easy to merge with cross_data
#' 
#' @import magrittr 
#' @importFrom dplyr group_by summarise
get_event_data <- function(controller_data) {
  controller_data$side <- parse_side(controller_data$hardware)
  
  event_data <- controller_data %>% group_by(hardware, group) %>%
    summarise(t_start = min(t_ms), t_end = max(t_ms), side = unique(side)) %>%
    mutate(idx = group) %>% select(-group)
   
  return(event_data)
}
