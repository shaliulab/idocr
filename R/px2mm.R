#' @export
px2mm <- function(lemdt_result, arena_width_mm=50, arena_width=125)  {
  lemdt_result$mm <- lemdt_result$cx/arena_width*arena_width_mm
  lemdt_result$mm <- lemdt_result$mm + arena_width_mm/2
  lemdt_result <- data.table::as.data.table(lemdt_result)
}