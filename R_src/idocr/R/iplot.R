preference_index_labeller <- function(x) {
  pi_val <- round(x, digits = 2)
  pi_val <- ifelse(is.na(pi_val), "NA", as.character(pi_val))
  pi_val <- stringr::str_pad(string = pi_val, width = 2, side = "left", pad = 0)
  pi_val
}

#' Generate base IDOC plot upon which
#' more annotation layers can be added
#' 
#' @import ggplot2
#' @export
iplot <- function(experiment_folder, data, limits, pi, run_id=NULL, plot_preference_index=TRUE) {
  
  theme_set(theme_bw())
  
  # breaks_limits <- sign(limits) * (round(abs(limits)/10) * 10 - 10)
  # breaks <- seq(from = breaks_limits[1], to = breaks_limits[2], by = 20)

  
  if (is.null(run_id)) {
    metadata <- load_metadata(experiment_folder)
    run_id <- metadata[field == "run_id", value]
  }
  
  data <- dplyr::full_join(data, pi, by="region_id")

  data$PI <- preference_index_labeller(data$preference_index)
  if (plot_preference_index) {
    browser()
    data$facet <- paste0("ROI_", data$region_id,"\nPI: ", data$PI)
  } else {
    data$facet <- paste0("ROI_", data$region_id)
  }
  data$facet <- factor(data$facet, levels = unique(data$facet))
  
  gg <- ggplot() +
    geom_line(
      data = data, mapping = aes(y = x, x = t),
      group = 1
    ) +
    labs(y = "Chamber", x = "t (s)") +
    scale_y_continuous(limits = limits, breaks = 0)
  

  gg <- gg + facet_wrap(
    . ~ facet,
    drop = F,
    nrow = 2, ncol = 10
  )
  
  gg <- gg + coord_flip() +
  ggtitle(label = run_id)
  
  return(gg)
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




