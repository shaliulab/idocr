#' @export
px2mm <- function(self)  {
  
  mm <- cx <- NULL
  lemdt_result <- self$lemdt_result
  
  lemdt_result[,mm := cx / self$arena_width * self$arena_width_mm + self$arena_width_mm / 2]
  self$lemdt_result <- lemdt_result
  
  return(self)
  
}