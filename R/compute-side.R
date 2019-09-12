#' import data.table
#' @export
compute_side <- function(lemdt_result, arena_width_mm=50, decision_zone_mm=5) {
  lemdt_result[, position := "L"]
  left_border <- (arena_width_mm - decision_zone_mm) / 2
  right_border <- left_border + decision_zone_mm
  lemdt_result[mm_mean >= left_border & mm_mean <= right_border, position := "D"]
  lemdt_result[mm_mean > right_border, position := "R"]
  return(lemdt_result)
}