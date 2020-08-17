#' Reshape controller data to a format where it is
#' easy to merge with cross_data
#' 
#' @import magrittr 
#' @importFrom dplyr group_by summarise
#' @export
get_event_data <- function(controller_data) {
  controller_data$side <- parse_side(controller_data$hardware_)
  
  event_data <- controller_data %>% group_by(hardware_, group) %>%
    summarise(t_start = min(t_ms), t_end = max(t_ms), side = unique(side)) %>%
    mutate(idx = group) %>% select(-group)
   
  event_data$hardware_small <- unlist(lapply(
    strsplit(event_data$hardware_, split = "_"),
    function(x) {
      paste(x[1:2], collapse = "_")
    }))
  
  return(event_data)
}
