#' import magrittr
#' @export
add_period_column <- function(lemdt_result) {
  # Define variable represeting the state of the system
  lemdt_result$period <- lemdt_result %>%
    apply(., 1, function(x) paste(x[c(
      'ODOUR_A_LEFT', 'ODOUR_A_RIGHT',
      'ODOUR_B_LEFT', 'ODOUR_B_RIGHT',
      'eshock_left', 'eshock_right')],
      collapse = '')
    )
  
  return(lemdt_result)
  
}