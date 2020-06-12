#' Generate base IDOC plot upon which
#' more annotation layers can be added
#' 
#' @import ggplot2
iplot <- function(data) {
  
  p <- ggplot() +
    # coord_flip() +
    geom_line(
      data = data, mapping = aes(y = x, x = t_ms / 1000),
      group = 1
    ) +
    
    labs(y = "Chamber", x = "t (s)") + 
    
    facet_wrap(
      ~region_id, nrow = 2, ncol = 10, drop = F,
      labeller = as_labeller(function(value) paste0("ROI_", value))
    ) +
    
    coord_flip()
  return(p)
}

#' Mark when a piece of IDOC hardware was active
#' in the form of a shape (usually a rectangle)
#' 
#' @import ggplot2
#' @importFrom ggforce geom_shape
add_shape <- function(shape_data) {
  
  shape <- geom_shape(
    data = shape_data,
    mapping = aes(y = x, x = y, group = group),
    #   # expand = unit(1, 'cm'),
    radius = unit(0.15, 'cm'),
    fill = "red", alpha = 0.4, color = "black"
  )
  
  return(shape)
}




