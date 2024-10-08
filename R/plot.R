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
mark_time <- function(data, gg, freq=60, downward=TRUE, orientation="y") {
  
  time_limits <- c(min(data$t), max(data$t))
  time_limits <- c(
    floor(time_limits[1] / freq) * freq,
    ceiling(time_limits[2] / freq) * freq
  )
  
  if (orientation == "y") {
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
  } else if (orientation=="x") {
    gg <- gg + scale_x_continuous(
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
mark_space <- function(limits, gg, extra=c(0), orientation="y") {
  breaks <- c(limits[1], extra, limits[2])
  if (orientation=="y") gg <- gg + scale_x_continuous(limits = limits, breaks = breaks, labels = round(breaks, digits = 0))
  else if (orientation=="x") gg <- gg + scale_y_continuous(limits = limits, breaks = breaks, labels = round(breaks, digits = 0))
  return(gg)
}


empty_canvas <- function() {
  theme_set(theme_bw() +
              theme(
                panel.spacing = unit(1, "lines"),
                text = element_text(size = 20)
              ) + theme(
                panel.grid.major = element_blank(),
                panel.grid.minor = element_blank()
              )
  )
  
  # initialize canvas
  gg <- ggplot()
  return(gg)
}

#' Generate base IDOC plot upon which
#' more annotation layers can be added
#' 
#' The base plot contains all individual panels,
#' dots to mark the fly positions
#' @eval document_data()
#' @param data 
#' @param limits
#' @param line_alpha Alpha of position trace
#' @param nrow Number of rows in facet layout
#' @param ncol Number of columns in facet layout
#' @inherit mark_space
#' @inherit mark_time
#' @import ggplot2
#' @eval document_gg("return")
#' @seealso [mark_space()]
#' @seealso [mark_time()]
#' @param nrow Number of rows used for facetting data
#' @param ncol Number of cols used for facetting data
#' @export
base_plot <- function(gg, data, limits, line_alpha=1, downward=TRUE, nrow=1, ncol=20, orientation="y") {

  x <- id <- NULL

  if (orientation=="y") {
    line <- geom_line(
      data = data, mapping = aes(x = x, y = t, group = id),
      # absolutely needed if we want to make a line plot with time on the y axis
      orientation=orientation,
      # intensity of line
      alpha=line_alpha
    )
  } else if (orientation=="x") {
    line <- geom_line(
      data = data, mapping = aes(x = t, y = x, group = id),
      # absolutely needed if we want to make a line plot with time on the y axis
      orientation=orientation,
      # intensity of line
      alpha=line_alpha
    )
  }
   
  # add line trace
  gg <- gg + line
  
  # add custom time marks (we want every 60 seconds)
  gg <- mark_time(data, gg, freq=60, downward=downward, orientation=orientation)
  gg <- mark_space(limits, gg, extra=c(0), orientation=orientation)
  
  if(length(unique(data$facet)) != (nrow * ncol)) {
    
    stop("The passed layout does not match the number of animals.
       Make sure nrow * ncol evaluates to the number of animals in the dataset ")
  }

  # segregate the animals, one plot for each
  gg <- gg + facet_wrap(
      . ~ facet,
      drop = F,
      nrow=nrow, ncol=ncol
    )
  
  return(gg)
}
  


#' Customize the facet label
#'
#' @eval document_data()
#' @param plot_preference_index Whether to show the scored preference index
#' with the region id on the facet label (TRUE), or just the region id (FALSE)
annotate_facet <- function(data, plot_preference_index=TRUE) {
  region_id <- paste0("ROI_", data$region_id)
  
  if (plot_preference_index) {
    data$facet <- paste0(region_id, "\nPI: ",
                         format_text(data$preference_index)
    )
    data$facet <- ifelse(is.na(data$preference_index), data$facet,
                         paste0(data$facet,
                                "\n(", data$appetitive, "|", data$aversive, ")"
                         ))
  } else {
    data$facet <- region_id
  }
  
  # make sure the facets have a numerical order
  # e.g. ROI_1 and then comes ROI_2, not ROI_10
  levels <- sort_facet_levels(data$facet)
  data$facet <- factor(data$facet, levels = levels)
  
  return(data)
}

#' Validate data passed to plot_dataset
#' @inherit plot_dataset
validate_inputs <- function(dataset, analysis) {
  expected_pi_columns <- c(
    "id", "region_id", "appetitive",
    "aversive", "preference_index", "test"
  )
  
  if (is.null(dataset$tracker))
    stop("Provided data frame under dataset$tracker slot is NULL.
         Please correct that by passing a non NULL data frame")
  if (!"data.frame" %in% class(dataset$tracker))
    stop("Provided a non data frame variable under dataset$tracker.
         Please correct that by passing a data frame")
  if (!all(sort(expected_pi_columns) == sort(colnames(analysis$pi))))
    stop(sprintf(
      "Provided a non valid preference index computation.
       You should provide a dataframe with columns: %s under analysis$pi",
      paste0(expected_pi_columns, collapse=" ")
    ))
  
  if (is.null(dataset$limits) || length(dataset$limits) != 2)
    stop("Provided limits under dataset$limits are NULL.
         Please provide a numeric vector of length 2 where you specify the minimum
         and maximum mm from the center of the chamber")
}

#' Distill the dataset and analysis performed in the idocr workflow
#' to the datasets required for plotting
#' 
#' A tracker dataset where every record represents the position
#' of one animal in one timepoint is required to plot the trace
#' 
#' A corssing dataset where every record represents a decision zone
#' exit of one animal is required to show the exits in the plot
#' @eval document_dataset()
#' @eval document_analysis()
#' @param plot_mask If not NULL, the plot contains data contained within
#' the interval's start and end (s)
#' @inherit annotate_facet
#' @importFrom dplyr left_join filter
combine_inputs <- function(dataset, analysis, plot_preference_index=TRUE, plot_mask=NULL) {
  
  . <- NULL
  
  tracker_data <- dplyr::left_join(dataset$tracker, analysis$pi, by = c("id", "region_id", "test"))
  crossing_data <- dplyr::left_join(analysis$annotation, analysis$pi, by = c("id", "region_id", "test"))
  
  message("Generating facet labels")
  tracker_data <- annotate_facet(tracker_data, plot_preference_index)
  crossing_data <- annotate_facet(crossing_data, plot_preference_index)
  
  if (!is.null(plot_mask)) {
    tracker_data <- tracker_data %>%
      dplyr::filter(., t >= plot_mask[1] & t <= plot_mask[2])
    
    crossing_data <- crossing_data %>%
      dplyr::filter(., t >= plot_mask[1] & t <= plot_mask[2])
  }
  
  return(list(
    tracker = tracker_data,
    crossing = crossing_data
  ))
}
#' Generate  an IDOC plot 
#'
#' Take a dataset and its analysis,
#' together with plotting parameters,
#' to visualize an IDOC experiment
#' @eval document_experiment_folder()
#' @eval document_dataset()
#' @eval document_analysis()
#' @param plot_decision_zone Whether to display the decision zone (TRUE) or not.
#' @param subtitle Character to write on the plot subtitles
#' @param colors Named vector of colors. Values should be colors
#' and names need to map to controller events
#' @param plot_crosses Whether to display the decision zone crosses (TRUE) or not.
#' @eval document_suffix()
#' @eval document_result_folder()
#' @inherit mark_analysis_mask
#' @inherit mark_stimuli
#' @inherit annotate_facet
#' @inherit mark_time
#' @inherit combine_inputs
#' @inherit base_plot
#' @param cross_size Size of dots used to represent decision zone exits (crosses)
#' @param ... Extra arguments for save_plot
#' @seealso [mark_stimuli()]
#' @seealso [mark_decision_zone()]
#' @seealso [mark_crosses()]
#' @seealso [save_plot()] 
#' @export
plot_dataset <- function(experiment_folder,
                         dataset, analysis,
                         result_folder = NULL,
                         plot_preference_index = TRUE,
                         plot_decision_zone = TRUE,
                         plot_crosses = TRUE,
                         subtitle = "",
                         colors = c(
                           "TREATMENT_A" = "red",
                           "TREATMENT_B" = "blue"
                         ),
                         labels = c(
                           "TREATMENT_A" = "TREATMENT_A",
                           "TREATMENT_B" = "TREATMENT_B"
                         ),
                         analysis_mask = NULL,
                         plot_mask = NULL,
                         downward=TRUE,
                         nrow=1, ncol=20,
                         suffix = "",
                         cross_size = 2,
                         line_alpha = 1,
                         do_mark_analysis_mask=TRUE,
                         do_document=TRUE,
                         orientation="y",
                         style="default",
                         ...
) {
  
  
  if (is.null(result_folder)) result_folder <- experiment_folder
  
  message("Validating passed data")
  validate_inputs(dataset, analysis)
  data <- combine_inputs(dataset, analysis,
                         plot_preference_index=plot_preference_index,
                         plot_mask=plot_mask
  )
  tracker_data <- data$tracker
  crossing_data <- data$crossing
  border <- dataset$border
  limits <- dataset$limits
  rectangles <- analysis$rectangles
  
  if (!is.null(dataset$labels) & all(labels == c("TREATMENT_A", "TREATMENT_B"))) {
    labels <- dataset$labels
  }
  
  gg <- empty_canvas()
  

  # add rectangular marks to sign the controller events
  message("Marking controller events")
  gg <- mark_stimuli(gg, rectangles, colors, labels, orientation=orientation)

  
  # initialize the plot by creating a tracker trace
  # for each animal separately
  message("Generating base plot")
  gg <- base_plot(
    gg,
    tracker_data, limits, downward=downward,
    line_alpha=line_alpha, nrow=nrow, ncol=ncol,
    orientation=orientation
  )
  
  
  if (!is.null(analysis_mask) && do_mark_analysis_mask) {
    message("Marking analysis mask")
    gg <- mark_analysis_mask(gg, analysis_mask, orientation=orientation)
  }
  # delineate the decision zone
  message("Marking decision zone")
  if (plot_decision_zone) gg <- mark_decision_zone(gg, border, orientation=orientation)
  
  # add points whenever an exit (decision zone cross) happens
  message("Marking decision zone crosses")
  if (plot_crosses) gg <- mark_crosses(gg, crossing_data, size=cross_size, orientation=orientation, style=style)
  
  # add text on axis, title, ...
  message("Documenting plot")
  if (do_document) {
      gg <- document_plot(gg, experiment_folder, subtitle=subtitle)
  }
  invisible(gg)
  
  # save the plot to the experiment's folder
  message("Saving plot to ->", experiment_folder)
  paths <- save_plot(gg, experiment_folder=experiment_folder, result_folder=result_folder, suffix=suffix, ...)
  
  return(list(paths=paths, plot=gg))
}

#' Mark the analysis mask
#' 
#' Mark the time interval of the experiment for which
#' the preference computation is performed
#' This is shown with a yellow rectangle in the plot
#' @eval document_gg()
#' @inherit find_exits
mark_analysis_mask <- function(gg, analysis_mask, orientation="y") {
  
  x <- y <- NULL
  box_size <- 1
  alpha <- 0.2
  color <- "yellow"
  
  limits <- gg$scales$scales[[3]]$limits
  mask_coords <- data.frame(
    x = rep(limits, times=2),
    y = rep(unlist(analysis_mask), each=2)
  )
  mask_coords <- mask_coords[c(1,2,4,3),]
  
  if (orientation=="y") {
    polygons <- geom_polygon(
      data = mask_coords,
      mapping = aes(x=x,y=y),
      color=color, alpha=alpha,
      fill=NA, size=box_size
    )
  } else if (orientation=="x") {
    polygons <- geom_polygon(
      data = mask_coords,
      mapping = aes(x=y,y=x),
      color=color, alpha=alpha,
      fill=NA, size=box_size
    )    
  }
  
  gg <- gg + polygons
  
  return(gg)
}

#' Annotate experiment metadata on plot for documentation
#' Users can write down particular features of their experiment
#' in the subtitle (frequency, duty cycle, odours, paradigms, etc)
#' A default title with the run id is generated if the experiment_folder is passed
#' A default caption with the current timestamp is placed on the bottom right
#' @eval document_gg()
#' @eval document_experiment_folder()
#' @param ... Extra arguments to ggplot2::labs
#' @seealso [ggplot2::labs()]
#' @return document_gg("return")
document_plot <- function(gg, experiment_folder=NULL, ...) {
  
  value <- field <- NULL
  
  if (!is.null(experiment_folder)) {
    metadata <- load_metadata(experiment_folder)
    title <- metadata[field == "date_time", value]
  } else {
    title <- ""
  }
  
  # TODO Make the call smarter by passing title and caption
  # only if the user did not provide them
  # If a user provides them, use them!
  gg <- gg +
    labs(
      x = "Chamber (mm)", y = "t (s)",
      title = title,
      caption = paste0("Produced on ", idocr_time()),
      ...
    )
  
  return(gg)
}

#' Mark stimuli / treatment action over time with rectangles on the plot 
#'  
#' @eval document_gg()
#' @param rectangles List of rectangle datasets where every dataset is a
#' dataframe of 4 rows describing the 4 corners of a rectangle.
#' They represent the occurrence of a stimulus each#' 
#' @param colors Named character vector where values are colors and names
#' are treatments. It establishes the color used to represent the treatments
#' on the plot
#' @param labels Character vector whose values become
#' the name of the treatments as rendered in the plot's legend
#' @importFrom purrr map
#' @import ggplot2
#' @return ggplot2 object
mark_stimuli <- function(gg, rectangles, colors, labels, orientation="y") {
  
  . <- x <- t <- group <- treatment <- NULL
  
  treatments <- names(colors)
  
  rectangles_df <- lapply(1:length(rectangles), function(i) {
    rectangles[[i]]$group <- i
    rectangles[[i]]
  }) %>%
    do.call(rbind, .)
  
  if (orientation=="y") {
    polygons <- geom_polygon(
      data = rectangles_df,
      mapping = aes(
        x = x, y=t,
        group=group,
        fill=treatment),
      color = NA, alpha=0.4
    )
  } else if (orientation=="x") {
    polygons <- geom_polygon(
      data = rectangles_df,
      mapping = aes(
        x = t, y=x,
        group=group,
        fill=treatment),
      color = NA, alpha=0.4
    )    
  }
  
  gg <- gg + polygons +
    scale_fill_manual(
      name = 'Treatment',
      values = unname(colors),
      labels = labels,
      guide = "legend"
    )
  
  return(gg)
}

#' Mark decision zone exit events (crosses)
#'
#' @eval document_gg()
#' @eval document_cross_data()
#' @param size Size of markers representing crosses 
#' @param color Color of the points, black by default
#' @importFrom dplyr select left_join
#' @import ggplot2
mark_crosses <- function(gg, cross_data, size=2, color="black", orientation="y", style="default") {
  
  x <- t <- NULL
  
  appetitive <- cross_data[cross_data$type == 'appetitive',]
  aversive <- cross_data[cross_data$type == 'aversive',]
  
  if (style == "default") {
    app_color <- color
    ave_color <- color
    app_shape <- 1
    ave_shape <- 4
  } else if (style == "poster") {
    app_color <- "#35b347"
    ave_color <- "#00abee"
    app_shape <- 16
    ave_shape <- 16
  }
  
  if (orientation=="y") {
    points_app <- geom_point(
      data = appetitive, aes(x = x, y = t),
      color = app_color, size = size, shape=app_shape
    )
    points_ave <- geom_point(
        data = aversive, aes(x = x, y = t),
        color = ave_color, size = size, shape = ave_shape
      )
  } else if (orientation=="x") {
    points_app <- geom_point(
      data = appetitive, aes(x = t, y = x),
      color = app_color, size = size, shape=app_shape
    )
    points_ave <- geom_point(
      data = aversive, aes(x = t, y = x),
      color = ave_color, size = size, shape = ave_shape
    )    
  }
  
  gg <- gg + points_app + points_ave
   
  
  return(gg)
}

#' Draw a dashed line to signal the decision zone
#'
#' @eval document_gg()
#' @param border Pixels between center and decision zone
#' @param center_alpha Transparency of line marking the center of the chamber
#' @eval document_gg("return")
#' @import ggplot2
mark_decision_zone <- function(gg, border, center_alpha=0.2, orientation="y") {
  if (orientation=="y") {
    gg <- gg + geom_vline(xintercept = -border, linetype = "dashed")
    gg <- gg + geom_vline(xintercept = border, linetype = "dashed") 
    gg <- gg + geom_vline(xintercept = 0, linetype="dashed", alpha=center_alpha)
  } else if (orientation=="x") {
    gg <- gg + geom_hline(yintercept = -border, linetype = "dashed")
    gg <- gg + geom_hline(yintercept = border, linetype = "dashed") 
    gg <- gg + geom_hline(yintercept = 0, linetype="dashed", alpha=center_alpha)    
  }
  return(gg)
}

#' Save a ggplot2 plot in pdf and png format using consistent naming
#' 
#' @param gg ggplot2 plot
#' @eval document_experiment_folder()
#' @eval document_result_folder()
#' @eval document_suffix()
#' @param ... Extra arguments for ggsave
#' @seealso [ggplot2::ggsave()]
#' @import ggplot2
save_plot <- function(gg, experiment_folder, result_folder=NULL, suffix="", ...) {
  
  field <- value <- NULL
  if (is.null(result_folder)) result_folder <- experiment_folder
  
  if (!is.null(experiment_folder) && any(grep(x = list.files(experiment_folder), pattern = "METADATA"))) {
    metadata <- load_metadata(experiment_folder)
    plot_basename <- sprintf(
      "%s_%s",
      metadata[field == "date_time", value],
      metadata[field == "machine_id", value]
    )
  } else {
    plot_basename <- "DUMMY"
  }
  
  plot_basename <- ifelse(suffix=="",
                          plot_basename,
                          paste0(plot_basename, "_", suffix)
  )
  
  
  # specify default width, height and dpi of plots
  ggsave_kwargs <- list(...)
  if (testthat_is_testing()) {
    width = ifelse(is.null(ggsave_kwargs$width), 16, ggsave_kwargs$width)
    height = ifelse(is.null(ggsave_kwargs$height), 16, ggsave_kwargs$height)
    dpi = ifelse(is.null(ggsave_kwargs$dpi), 16, ggsave_kwargs$dpi)
  } else {
    width = ifelse(is.null(ggsave_kwargs$width), 25, ggsave_kwargs$width)
    height = ifelse(is.null(ggsave_kwargs$height), 12, ggsave_kwargs$height)
    dpi = ifelse(is.null(ggsave_kwargs$dpi), "print", ggsave_kwargs$dpi)
  }
  
  paths <- list()
  
  for (extension in c('pdf', 'png')) {
    message("Saving ", extension, " format")
    plot_filename <- sprintf(
      "%s.%s",
      plot_basename,
      extension
    )
    path <- file.path(result_folder, plot_filename)
    paths[[extension]] <- path
    
    # save!
    suppressMessages(ggsave(
      filename = path,
      plot = gg,
      width=width, height=height, dpi=dpi
    ))
  }
  return(paths)
  
}
