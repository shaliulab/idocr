#' @importFrom stringr str_pad
preference_index_labeller <- function(x) {
  pi_val <- round(x, digits = 2)
  pi_val <- ifelse(is.na(pi_val), "NA", as.character(pi_val))
  pi_val <- stringr::str_pad(string = pi_val, width = 2, side = "left", pad = 0)
  pi_val
}

#' @importFrom stringr str_match
sort_roi_level <- function(roi_level) {
  levels <- unique(roi_level)
  matches <- stringr::str_match(string = levels, pattern = "ROI_(\\d{1,2})\nPI: -?.*")
  matches <- as.integer(matches[,2])
  names(matches) <- levels
  sorted_levels <- names(sort(matches))
  return(sorted_levels)
}

#' Generate base IDOC plot upon which
#' more annotation layers can be added
#' 
#' @import ggplot2
#' @importFrom glue glue
#' @importFrom dplyr full_join
#' @export
base_plot <- function(experiment_folder, data, limits, pi, run_id=NULL, plot_preference_index=TRUE, subtitle = "") {
  
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
    data$facet <- paste0("ROI_", data$region_id,"\nPI: ", data$PI)
  } else {
    data$facet <- paste0("ROI_", data$region_id)
  }
  
  # browser()
  
  levels <- sort_roi_level(data$facet)
  data$facet <- factor(data$facet, levels = levels)
  
  gg <- ggplot() +
    geom_line(
      data = data, mapping = aes(y = x, x = t),
      group = 1
    ) +
    labs(y = "Chamber (mm)", x = "t (s)", title = run_id, subtitle = ,
         caption = glue::glue('Produced on {Sys.time()}')) +
    scale_y_continuous(limits = limits, breaks = c(limits[1], 0, limits[2]))
  ## DANGER! this plot is likely to break studio if rendered now
  
  time_limits <- c(min(data$t), max(data$t))
  time_limits <- c(floor(time_limits[1] / 60) * 60, ceiling(time_limits[2] / 60) * 60)
  
  gg <- gg +
    scale_x_continuous(limits = time_limits,
                       breaks = seq(
                         from = time_limits[1],
                         to = time_limits[2],
                         by = 60)
                       )
  
  
  gg <- gg + facet_wrap(
    . ~ facet,
    drop = F,
    nrow = 2, ncol = 10
  ) + theme(panel.spacing = unit(1, "lines"))
  
  gg <- gg + coord_flip() + theme(text = element_text(size = 20))
  # it is ok to render now as the coords have been flipped
  
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





#' @export
idoc_plot <- function(experiment_folder, roi_data, rectangle_data,
                      preference_data, pi_data,
                      CSplus, CSminus, border, limits,
                      side_agnostic_hardware = NULL,
                      plot_preference_index=TRUE,
                      plot_decision_zone=TRUE,
                      plot_basename = NULL,
                      old_mapping = FALSE,
                      subtitle = ""
                      ) {
  
  # To order the region_id s in the old way
  if (old_mapping) {
    mapper <- c(1,3,5,7,9,11,13,15,17,19,2,4,6,8,10,12,14,16,18,20)
    names(mapper) <- 1:20
    roi_data$region_id <- mapper[roi_data$region_id]
  }
  
  
  apetitive <- preference_data[preference_data$type == 'apetitive',]
  aversive <- preference_data[preference_data$type == 'aversive',]
  
  preference_data <- dplyr::left_join(preference_data, pi_data, by = "region_id")
  
  if (plot_preference_index) {
     preference_data$facet <- paste0("ROI_", preference_data$region_id, "\nPI: ", preference_index_labeller(preference_data$preference_index))
  } else {
    preference_data$facet <- paste0("ROI_", preference_data$region_id)
  }
  
  levels <- sort_roi_level(preference_data$facet)
  preference_data$facet <- factor(preference_data$facet, levels = levels)
  
  apetitive <- preference_data[preference_data$type == 'apetitive',]
  aversive <- preference_data[preference_data$type == 'aversive',]
  
  colors <- c("red", "blue")[1:length(side_agnostic_hardware)]
  names(colors) <- side_agnostic_hardware 
  
  gg <- base_plot(
    experiment_folder, roi_data, limits,
    run_id = rev(unlist(strsplit(experiment_folder, split = '/')))[1],
    pi = pi_data, plot_preference_index = plot_preference_index, subtitle = subtitle
  )

  rectangles <- rectangle_data %>%
    purrr::map(~add_polygon(., color = colors[unique(.$hardware_small)]))
  
  for (rect in rectangles) {
    gg <- gg + rect
  }
  
  gg <- gg +
    scale_fill_identity(name = 'Treatment', breaks = colors, labels = names(side_agnostic_hardware),
                        guide = "legend") +
    guides(color = F)
  
  gg <- gg +
    geom_point(data = apetitive, aes(x = t, y = x), color = "black", size = 5) +
    geom_point(data = aversive, aes(x = t, y = x), color = "black", size = 5, shape = 4)
  
  
  border_lines <- list(
    geom_hline(yintercept = -border, linetype = "dashed"),
    geom_hline(yintercept = border, linetype = "dashed") 
  )
  
  if (isTRUE(plot_decision_zone)) {
    for (b_line in border_lines) {
      gg <- gg + b_line
    }
  }
  
  
  metadata <- load_metadata(experiment_folder)
  if (is.null(plot_basename)) {
    plot_basename <- sprintf(
      "%s_%s",
      metadata[field == "date_time", value],
      metadata[field == "machine_id", value]
    )
  }
  
  for (extension in c('pdf', 'png')) {
    plot_filename <- sprintf(
      "%s.%s",
      plot_basename,
      extension
    )
    ggplot2::ggsave(filename = file.path(experiment_folder, plot_filename), width = 25, height = 12)
  }
  return(gg)
}



