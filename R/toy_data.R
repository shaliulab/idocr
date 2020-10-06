toy_raw <- function(dataset) {
  experiment_folder <- system.file(dataset, package = "idocr")
  load_rois(experiment_folder)
}

toy_controller <- function(dataset) {
  experiment_folder <- system.file(dataset, package = "idocr")
  load_controller(experiment_folder)
}

# toy_crosses <- function() {
#   experiment_folder <- system.file("example", package = "idocr")
#   hardware = c("TREATMENT_A_LEFT",  "TREATMENT_A_RIGHT", "TREATMENT_B_LEFT",  "TREATMENT_B_RIGHT")
#   old_mapping = FALSE
#   plot_basename = NULL
#   border_mm = 5
#   min_exits_required = 5
#   
#   pixel_to_mm_ratio <- 2.3
#   border <- border_mm * pixel_to_mm_ratio
#   rect_pad <- 0
#   
#   border_lines <- list(
#     geom_hline(yintercept = -border, linetype = "dashed"),
#     geom_hline(yintercept = border, linetype = "dashed") 
#   )
#   
#   plot_decision_zone <- TRUE
#   plot_preference_index <- TRUE
#   
#   
#   roi_data <- load_rois(experiment_folder)
#   # To order the region_id s in the old way
#   if (old_mapping) {
#     mapper <- c(1,3,5,7,9,11,13,15,17,19,2,4,6,8,10,12,14,16,18,20)
#     names(mapper) <- 1:20
#     roi_data$region_id <- mapper[roi_data$region_id]
#   }
#   
#   controller_data <- load_controller(experiment_folder)
#   
#   controller_data <- purrr::map(
#     hardware,
#     ~prepare_shape_data(
#       controller_data = controller_data,
#       hardware = .
#     )
#   ) %>%
#     do.call(rbind, .) %>%
#     dplyr::mutate(t_ms = t * 1000)
#   
#   controller_data$hardware_small <- unlist(lapply(
#     strsplit(controller_data$hardware_, split = "_"),
#     function(x) {
#       paste(x[1:2], collapse = "_")
#     }))
#   
#   limits <- c(min(roi_data$x), max(roi_data$x))
#   
#   unique_hardware <- unique(controller_data$hardware_small)
#   colors <- c("red", "blue")[1:length(unique_hardware)]
#   names(colors) <- unique_hardware 
#   
#   rects <- controller_data %>%
#     dplyr::group_by(hardware_) %>%
#     dplyr::group_split() %>%
#     purrr::map(~scale_shape(., limits, rect_pad))
#   
#   rects <- rects %>%
#     purrr::map(~add_polygon(., color = colors[unique(.$hardware_small)]))
#   
#   roi_data_plot <- add_empty_roi(experiment_folder, roi_data)
#   
#   gg <- base_plot(
#     experiment_folder, roi_data_plot, limits,
#     run_id = rev(unlist(strsplit(experiment_folder, split = '/')))[1]
#   )
#   
#   for (rect in rects) {
#     gg <- gg + rect
#   }
#   
#   gg <- gg +
#     scale_fill_identity(name = 'Hardware', breaks = colors, labels = unique_hardware,
#                         guide = "legend") +
#     guides(color = F)
#   
#   cross_data <- rbind(
#     gather_cross_data(cross_detector_FUN = cross_detector, roi_data, border = border, side = 1),
#     gather_cross_data(cross_detector_FUN = cross_detector, roi_data, border = border, side = -1)
#   )
#   
#   event_data <- get_event_data(controller_data)
#   
#   # TODO Beyond should be TRUE when the cross is outside of the decision zone
#   # However, it is opposite
#   preference <- overlap_cross_events(
#     cross_data[cross_data$beyond,],
#     event_data[event_data$hardware_small == "TREATMENT_A",],
#     type = "preference", mask_FUN = seconds_mask
#   )
#   
#   aversive <- overlap_cross_events(
#     cross_data[cross_data$beyond,],
#     event_data[event_data$hardware_small == "TREATMENT_B",],
#     type = "aversive", mask_FUN = seconds_mask
#   )
#   
#   return(list(preference = preference, aversive = aversive))
# }
