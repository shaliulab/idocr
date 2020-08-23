#' The standard idocr workflow.
#' 
#' Load data from the experiment folder, possibly with some specific settings
#' and return a data frame with the preference index of each fly
#' and a plot visualizing the experiment
#' @importFrom dplyr nest_by summarise group_by
#' @import ggplot2
#' @importFrom purrr map
#' @export
idocr <- function(experiment_folder, hardware = c("TREATMENT_A_LEFT",  "TREATMENT_A_RIGHT", "TREATMENT_B_LEFT",  "TREATMENT_B_RIGHT"),
                  old_mapping = FALSE, plot_basename = NULL, border_mm = 5, min_exits_required = 5, CSplus="TREATMENT_A", plot_preference_index=TRUE) {
  
  
  marked_hardware <- unique(unlist(lapply(
    strsplit(hardware, split = "_"),
    function(x) {
      paste(x[1:2], collapse = "_")
    })))
  
  CSminus <- marked_hardware[marked_hardware != CSplus]

  
  # Convert human understandable mm
  # to pixels that are easy to work with in R
  pixel_to_mm_ratio <- 2.3
  border <- border_mm * pixel_to_mm_ratio
  rect_pad <- 0
  
  border_lines <- list(
    geom_hline(yintercept = -border, linetype = "dashed"),
    geom_hline(yintercept = border, linetype = "dashed") 
  )
  
  plot_decision_zone <- TRUE
  
  roi_data <- load_rois(experiment_folder)
  # To order the region_id s in the old way
  if (old_mapping) {
    mapper <- c(1,3,5,7,9,11,13,15,17,19,2,4,6,8,10,12,14,16,18,20)
    names(mapper) <- 1:20
    roi_data$region_id <- mapper[roi_data$region_id]
  }
  
  controller_data <- load_controller(experiment_folder)
  
  controller_data <- purrr::map(
    hardware,
    ~prepare_shape_data(
      controller_data = controller_data,
      hardware = .
    )
  ) %>%
    do.call(rbind, .) %>%
    dplyr::mutate(t_ms = t * 1000)
  
  controller_data$hardware_small <- unlist(lapply(
    strsplit(controller_data$hardware_, split = "_"),
    function(x) {
      paste(x[1:2], collapse = "_")
    }))
  
  limits <- c(min(roi_data$x), max(roi_data$x))
  
  unique_hardware <- unique(controller_data$hardware_small)
  colors <- c("red", "blue")[1:length(unique_hardware)]
  names(colors) <- unique_hardware 
  
  roi_data_plot <- add_empty_roi(experiment_folder, roi_data)
  
  
  cross_data <- rbind(
    gather_cross_data(cross_detector_FUN = cross_detector, roi_data, border = border, side = 1),
    gather_cross_data(cross_detector_FUN = cross_detector, roi_data, border = border, side = -1)
  )
  
  event_data <- get_event_data(controller_data)
  
  # TODO Beyond should be TRUE when the cross is outside of the decision zone
  # However, it is opposite
  preference <- overlap_cross_events(
    cross_data[cross_data$beyond,],
    event_data[event_data$hardware_small == CSplus,],
    type = "preference", mask_FUN = seconds_mask
  )
  
  aversive <- overlap_cross_events(
    cross_data[cross_data$beyond,],
    event_data[event_data$hardware_small == CSminus,],
    type = "aversive", mask_FUN = seconds_mask
  )
  
  overlap_data <- rbind(
    cbind(
      preference,
      type = "preference"
    ),
    cbind(
      aversive,
      type = "aversive"
    )
  )
  
  pi_data <- overlap_data %>%
    dplyr::nest_by(region_id) %>%
    dplyr::summarise(preference_index = preference_index(data, min_exits_required = min_exits_required))
  
  if (plot_preference_index) {
    preference <- dplyr::left_join(preference, pi_data, by = "region_id")
    preference$facet <- paste0("ROI_", preference$region_id, "\nPI: ", preference_index_labeller(preference$preference_index)) 
    aversive <- dplyr::left_join(aversive, pi_data, by = "region_id")
    aversive$facet <- paste0("ROI_", aversive$region_id, "\nPI: ", preference_index_labeller(aversive$preference_index))
  } else {
    aversive$facet <- paste0("ROI_", aversive$region_id)
    preference$facet <- paste0("ROI_", preference$region_id)
  }
  aversive$facet <- factor(aversive$facet, levels = unique(aversive$facet))
  preference$facet <- factor(preference$facet, levels = unique(preference$facet))
  
  
  gg <- iplot(
    experiment_folder, roi_data_plot, limits,
    run_id = rev(unlist(strsplit(experiment_folder, split = '/')))[1],
    pi = pi_data, plot_preference_index = plot_preference_index
  )
  
  rects <- controller_data %>%
    dplyr::group_by(hardware_) %>%
    dplyr::group_split() %>%
    purrr::map(~scale_shape(., limits, rect_pad))
  
  rects <- rects %>%
    purrr::map(~add_polygon(., color = colors[unique(.$hardware_small)]))
  
  for (rect in rects) {
    gg <- gg + rect
  }
  
  gg <- gg +
    scale_fill_identity(name = 'Hardware', breaks = colors, labels = unique_hardware,
                        guide = "legend") +
    guides(color = F)
  
  gg <- gg +
    geom_point(data = preference, aes(x = t, y = x), color = "black", size = 1) +
    geom_point(data = aversive, aes(x = t, y = x), color = "black", size = 1, shape = 4)
  
  gg
  
  if(plot_decision_zone == TRUE) {
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
    ggplot2::ggsave(filename = file.path(experiment_folder, plot_filename))
  }
  
  return(list(gg = gg, pi = pi_data))
}
