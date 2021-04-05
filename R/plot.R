#' Format text so numbers on it are rendered consistently
#' 
#' @param text Character text to be formatted
#' @importFrom stringr str_pad
#' @return Formatted character
format_text <- function(text) {
  
  # single values
  formatter <- function(x) {
    y <- round(x, digits = 2)
    y <- ifelse(is.na(y), "NA", as.character(y))
    y <- stringr::str_pad(string = y, width = 2, side = "left", pad = 0)
    return(y)
  }
  
  y <- lapply(text, function(x) {
    ifelse(is.character(x), x, as.character(formatter(x)))
  })
  return(y)
}

# @importFrom stringr str_match
#' Enforce a numeric sorting of facets for visualization
#' @importFrom gtools mixedsort
#' @param facets Character of facets to be sorted
#' @return Facet levels sorted in numeric order
#' (ROI_1, ROI_2, ..., ROI_19, ROI_20)
sort_facet_levels <- function(facets) {
  facets <- unique(facets)
  sorted_facets <- gtools::mixedsort(facets)
  # TODO Remove commented code if mixedsort does the job
  #matches <- stringr::str_match(string = facets, pattern = "ROI_(\\d{1,2})\nPI: -?.*")
  #matches <- as.integer(matches[,2])
  #names(matches) <- levels
  #sorted_facets <- names(sort(matches))
  return(sorted_facets)
}


#' Mark time with a custom frequency
#'
#' Place the ticks on the time axis with an intuitive frequency
#' @eval document_data()
#' @eval document_gg()
#' @param freq Number of seconds in between axis ticks, 60 by default
#' @param downward Whether the 0 should be at the top (TRUE)
#' or the bottom (FALSE) of the plot
#' @importFrom scales reverse_trans
#' @import ggplot2
#' @return ggplot2 object
mark_time <- function(data, gg, freq=60, downward=TRUE) {
  
  time_limits <- c(min(data$t), max(data$t))
  time_limits <- c(
    floor(time_limits[1] / freq) * freq,
    ceiling(time_limits[2] / freq) * freq
  )
  
  if (downward) {
    gg <- gg + scale_y_continuous(
      limits = rev(time_limits),
      breaks = seq(
        from = time_limits[2],
        to = time_limits[1],
        by = -freq
      ),
      trans = scales::reverse_trans()
    )
  } else {
    gg <- gg + scale_y_continuous(
      limits = time_limits,
      breaks = seq(
        from = time_limits[1],
        to = time_limits[2],
        by = freq
      )
    )
  }
  return(gg)
}

#' Mark space
#' Place the ticks on the space axis so visualization is convenient
#' @eval document_limits()
#' @eval document_gg()
#' @param extra Position of ticks in space besides limits
#' @import  ggplot2
#' @eval document_gg("return")
mark_space <- function(limits, gg, extra=c(0)) {
  breaks <- c(limits[1], extra, limits[2])
  gg <- gg + scale_x_continuous(limits = limits, breaks = breaks)
  return(gg)
}


#' Generate base IDOC plot upon which
#' more annotation layers can be added
#' 
#' The base plot contains all individual panels,
#' dots to mark the fly positions
#' @eval document_data()
#' @inherit mark_space
#' @import ggplot2
#' @eval document_gg("return")
#' @export
base_plot <- function(data, limits) {

  theme_set(theme_bw() + theme(
    panel.spacing = unit(1, "lines"),
    text = element_text(size = 20))
  )

  # initialize canvas
  gg <- ggplot()
  
  # add line trace
  gg <- gg +
    geom_line(
      data = data, mapping = aes(x = x, y = t, group = id),
      orientation="y"
    )
  
  # add custom time marks (we want every 60 seconds)
  gg <- mark_time(data, gg, freq=60)
  gg <- mark_space(limits, gg, extra=c(0))

  # segregate the animals, one plot for each
  gg <- gg + facet_wrap(
    . ~ facet,
    drop = F,
    nrow = 2, ncol = 10
  )

  return(gg)
}

#' Generate a rectangle object
#' that will mark a piece of IDOC hardware was active
#' 
#' @eval document_shape_data()
#' @param color Rectangle fill color
#' @param border Rectangle border color
#' @param alpha Rectangle transparency
#' @import ggplot2
#' @return ggplot2 geom_polygon
#' @export
make_rectangle <- function(shape_data, color="red", border="black", alpha=0.4) {
  
  shape <- geom_polygon(
    data = shape_data,
    mapping = aes(
      y = t, x = x, group = group,
    ),
    alpha = alpha, fill = color, color = border
  )
  return(shape)
}


#' Customize the facet label
#'
#' @eval document_data()
#' @param plot_preference_index If TRUE, the PI displayed by the animal is
#' put into the facet label
annotate_facet <- function(data, plot_preference_index=TRUE) {
  region_id <- paste0("ROI_", data$region_id)

  if (plot_preference_index) {
    data$facet <- paste0(region_id, "\nPI: ", format_text(data$preference_index))
  } else {
    data$facet <- region_id
  }

  # make sure the facets have a numerical order
  # e.g. ROI_1 and then comes ROI_2, not ROI_10
  levels <- sort_facet_levels(data$facet)
  data$facet <- factor(data$facet, levels = levels)
  
  return(data)
}

#' Generate  an IDOC plot 
#'
#' Take a dataset and its analysis,
#' together with plotting parameters,
#' to visualize an IDOC experiment
#' @eval document_experiment_folder()
#' @eval document_dataset()
#' @eval document_analysis()
#' @param plot_preference_index Whether to show the scored preference index
#' with the region id on the facet label (TRUE), or just the region id (FALSE)
#' @param plot_decision_zone Whether to display the decision zone (TRUE) or not.
#' @param subtitle Character to write on the plot subtitles
#' @param colors Named vector of colors. Values should be colors
#' and names need to map to controller events
#' @param ... Extra arguments for save_plot
#' @importFrom dplyr left_join
#' @seealso [mark_stimuli()]
#' @seealso [mark_decision_zone()]
#' @seealso [mark_crosses()]
#' @seealso [save_plot()] 
#' @export
plot_dataset <- function(experiment_folder, dataset, analysis,
                         plot_preference_index=TRUE,
                         plot_decision_zone=TRUE,
                         subtitle = "",
                         colors = c("TREATMENT_A" = "red", "TREATMENT_B" = "blue"),
                         ...
                         ) {
  
  data <- dplyr::left_join(dataset$roi, analysis$pi, by = "region_id")
  data <- annotate_facet(data, plot_preference_index)
  
  # initialize the plot by creating a tracking trace for each animal
  # separately
  message("Generating base plot")
  gg <- base_plot(data, dataset$limits)
  
  message("Refinning axis ticks")
  # customize the x axis (chamber width)
  # we want to mark where the 0 is

  
  message("Marking controller events")
  # add rectangular marks to sign the controller events
  gg <- mark_stimuli(gg, analysis, colors)
  
  message("Marking decision zone")
  # delineate the decision zone
  if (plot_decision_zone) gg <- mark_decision_zone(gg, dataset$border)
  
  message("Marking decision zone crosses")
  # add points whenever an exit (decision zone cross) happens
  gg <- mark_crosses(gg, data, analysis)
  
  message("Documenting plot")
  # add text on axis, title, ...
  metadata <- load_metadata(experiment_folder)
  run_id <- metadata[field == "run_id", value]
  
  gg <- gg +
    labs(x = "Chamber (mm)", y = "t (s)",
         title = run_id, subtitle = subtitle,
         caption = paste0("Produced on ", Sys.time()))
  
  message("Saving plot to ->", experiment_folder)
  # save the plot to the experiment's folder
  save_plot(gg, experiment_folder, ...)
  
  return(gg)
}

#' Mark stimuli / treatment action over time with rectangles on the plot 
#'  
#' @eval document_gg()
#' @eval document_analysis()
#' @param colors Named character vector where values are colors and names
#' are treatments. It establishes the color used to represent the treatments
#' on the plot
#' @importFrom purrr map
#' @import ggplot2
#' @return ggplot2 object
mark_stimuli <- function(gg, analysis, colors) {
  
  treatments <- names(colors)
  
  rectangles <- analysis$rectangles %>%
    purrr::map(~make_rectangle(., color = colors[unique(.$treatment)]))
  
  for (rect in rectangles) {
    gg <- gg + rect
  }
  
  gg <- gg +
    scale_fill_identity(name = 'Treatment', breaks = colors,
                        guide = "legend") +
    guides(color = F)
  return(gg)
}

#' Mark decision zone exit events (crosses)
#'
#' @eval document_gg()
#' @eval document_data()
#' @eval document_analysis()
#' @importFrom dplyr select left_join
#' @import ggplot2
mark_crosses <- function(gg, data, analysis) {
  
  analysis$annotation <- dplyr::left_join(
    analysis$annotation,
    dplyr::select(data, region_id, facet),
    by = "region_id"
  )
  
  appetitive <- analysis$annotation[analysis$annotation$type == 'appetitive',]
  aversive <- analysis$annotation[analysis$annotation$type == 'aversive',]
  
  gg <- gg +
    geom_point(
      data = appetitive, aes(x = x, y = t),
      color = "black", size = 2
    ) +
    geom_point(
      data = aversive, aes(x = x, y = t),
      color = "black", size = 2, shape = 4
    )
  
  return(gg)
}

#' Draw a dashed line to signal the decision zone
#'
#' @eval document_gg()
#' @param border Pixels between center and decision zone
#' @eval document_gg("return")
#' @import ggplot2
mark_decision_zone <- function(gg, border) {
  gg <- gg + geom_vline(xintercept = -border, linetype = "dashed")
  gg <- gg + geom_vline(xintercept = border, linetype = "dashed") 
  return(gg)
}

#' Save a ggplot2 plot in pdf and png format using consistent naming
#' 
#' @param gg ggplot2 plot
#' @eval document_experiment_folder()
#' @import ggplot2
save_plot <- function(gg, experiment_folder, ...) {
  
  metadata <- load_metadata(experiment_folder)
  plot_basename <- sprintf(
    "%s_%s",
    metadata[field == "date_time", value],
    metadata[field == "machine_id", value]
  )
  
  # specify default width, height and dpi of plots
  ggsave_kwargs <- list(...)
  width = ifelse(is.null(ggsave_kwargs$width), 16, ggsave_kwargs$width)
  height = ifelse(is.null(ggsave_kwargs$height), 16, ggsave_kwargs$height)
  dpi = ifelse(is.null(ggsave_kwargs$dpi), 16, ggsave_kwargs$dpi)
  
  for (extension in c('pdf', 'png')) {
    message("Saving ", extension, " format")
    plot_filename <- sprintf(
      "%s.%s",
      plot_basename,
      extension
    )
    
    # save!
    ggsave(
      filename = file.path(experiment_folder, plot_filename),
      width=width, height=height, dpi=dpi
    )
  }
}
