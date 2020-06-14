#' @export
main <- function(experiment_folder, hardware = c('LED_R_LEFT', 'LED_R_RIGHT'),  old_mapping = FALSE, plot_basename = NULL, border = 10, min_exits_required = 5) {
  
  # experiment_folder <- "/learnmem_data/results/be979e46217f3a5ec0f254245eb68da5/ANTORTJIM-LAPTOP/2020-06-09_21-33-57/"
  # experiment_folder <- "/1TB/Cloud/Data/idoc_data/results/7eb8e224bdb944a68825986bc70de6b1/FLYSLEEPLAB_SETUP/2020-06-10_19-56-36"
  # experiment_folder <- "/1TB/Cloud/Data/idoc_data/results/be979e46217f3a5ec0f254245eb68da5/ANTORTJIM-LAPTOP/2020-06-10_11-53-34/"
  
  # border <- 10
  rect_pad <- 0
  # min_exits_required <- 5
  
  # metadata <- load_metadata(experiment_folder)
  # run_id <- metadata[field == "run_id", value]
  
  border_lines <- list(
    geom_hline(yintercept = -border, linetype = "dashed"),
    geom_hline(yintercept = border, linetype = "dashed") 
  )
  plot_decision_zone <- TRUE
  plot_preference_index <- TRUE
  
  
  roi_data <- load_rois(experiment_folder)
  colnames(roi_data)
  # To order the region_id s in the old way
  if (old_mapping) {
    mapper <- c(1,3,5,7,9,11,13,15,17,19,2,4,6,8,10,12,14,16,18,20)
    names(mapper) <- 1:20
    roi_data$region_id <- mapper[roi_data$region_id]
  }
  
  controller_data <- load_controller(experiment_folder)
  
  controller_data <- map(
    hardware,
    ~prepare_shape_data(
        controller_data = controller_data,
        hardware = .
    )
  ) %>%
    do.call(rbind, .) %>%
    mutate(t_ms = t * 1000)
  
  limits <- c(min(roi_data$x), max(roi_data$x))
  rects <- controller_data %>%
    group_by(hardware) %>%
    group_split() %>%
    map(~scale_shape(., limits, rect_pad)) %>%
    map(~add_polygon(., color = "red"))
  
  roi_data_plot <- add_empty_roi(experiment_folder, roi_data)
  

  
  p <- iplot(
    experiment_folder, roi_data_plot, limits,
    run_id = rev(unlist(strsplit(experiment_folder, split = '/')))[1]
  )
  
  for (rect in rects) {
    p <- p + rect
  }
  p <- p + scale_fill_identity(name = 'Hardware', breaks = 'red', labels = 'LED_R', guide = "legend") + guides(color = F)
  
  cross_data <- rbind(
    gather_cross_data(cross_detector_FUN = cross_detector, roi_data, border = border, side = 1),
    gather_cross_data(cross_detector_FUN = cross_detector, roi_data, border = border, side = -1)
  )
  
  event_data <- get_event_data(controller_data)
  
  # TODO Beyond should be TRUE when the cross is outside of the decision zone
  # However, it is opposite
  preference <- overlap_cross_events(
    cross_data[!cross_data$beyond,],
    event_data, type = "preference", mask_FUN = seconds_mask
  )
  aversive <- overlap_cross_events(
    cross_data[!cross_data$beyond,],
    event_data, type = "aversive", mask_FUN = seconds_mask
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
    nest_by(region_id) %>%
    summarise(preference_index = preference_index(data, min_exits_required = min_exits_required))
  
  p <- p +
    geom_point(data = preference, aes(x = t, y = x), size = 1) +
    geom_point(data = aversive, aes(x = t, y = x), size = 1, color = "blue", shape = 4)
  
  
  if(plot_decision_zone == TRUE) {
    for (b_line in border_lines) {
      p <- p + b_line
    }
  }
  
  if(plot_preference_index == TRUE) {
  
    p <- p +
      # ggnewscale::new_scale_fill() +
      geom_label(
        data = pi_data,
        aes(
          label = stringr::str_pad(string = round(preference_index, digits = 2), width = 3, pad = 0)
        ),
        fontface = 'bold', color = 'black', y = 0, x = 1, size = 5)
    
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

  return(p)
}