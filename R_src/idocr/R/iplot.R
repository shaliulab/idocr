#' Generate base IDOC plot upon which
#' more annotation layers can be added
#' 
#' @import ggplot2
#' @export
iplot <- function(experiment_folder, data, limits, run_id=NULL) {
  
  theme_set(theme_bw())
  
  # breaks_limits <- sign(limits) * (round(abs(limits)/10) * 10 - 10)
  # breaks <- seq(from = breaks_limits[1], to = breaks_limits[2], by = 20)

  
  if (is.null(run_id)) {
    metadata <- load_metadata(experiment_folder)
    run_id <- metadata[field == "run_id", value]
  }
  
  p <- ggplot() +
    # coord_flip() +
    geom_line(
      data = data, mapping = aes(y = x, x = t),
      group = 1
    ) +
    
    labs(y = "Chamber", x = "t (s)") +
    scale_y_continuous(limits = limits, breaks = 0) +
    facet_wrap(
      ~region_id, nrow = 2, ncol = 10, drop = F,
      labeller = as_labeller(function(value) paste0("ROI_", value))
    ) +
    coord_flip() +
    ggtitle(label = run_id)
  
  return(p)
}

#' Mark when a piece of IDOC hardware was active
#' in the form of a shape (usually a rectangle)
#' 
#' @import ggplot2
#' @importFrom ggforce geom_shape
#' @export
add_shape <- function(shape_data, color="red", border="black") {
  
  shape <- geom_shape(
    data = shape_data,
    mapping = aes(y = x, x = t, group = group),
    #   # expand = unit(1, 'cm'),
    radius = unit(0.15, 'cm'),
    fill = color, alpha = 0.4, color = border
  )
  
  return(shape)
}


#' Mark when a piece of IDOC hardware was active
#' in the form of a polygon (usually a rectangle)
#' 
#' @import ggplot2
#' @importFrom ggforce geom_shape
#' @export
add_polygon <- function(shape_data, color="red", border="black") {
  
  shape <- geom_polygon(
    data = shape_data,
    mapping = aes(
      y = x, x = t, group = group,
      fill = color, color = border
    ), alpha = 0.4
    
  )
  
  return(shape)
}




