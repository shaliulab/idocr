#' @export
px2mm <- function(self)  {
  
  lemdt_result <- self$lemdt_result
  
  lemdt_result[,mm := cx / self$arena_width * self$arena_width_mm]
  lemdt_result$mm <- lemdt_result$mm + self$arena_width_mm / 2
  
  self$lemdt_result <- lemdt_result
  
  return(self)
  
}