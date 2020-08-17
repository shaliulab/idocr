library(data.table)
library(purrr)
library(dplyr)
library(gtools)
library(ggplot2)
library(ggforce)
## --------------------------------------

#' Load the data of an IDOC experiment
#' @importFrom data.table fread
#' @importFrom purrr map imap
#' @importFrom dplyr mutate
load_idoc <- function(experiment_folder) {

 csv_files <- list.files(path = experiment_folder, pattern = ".csv")
 controller_data <- load_controller(experiment_folder)
 roi_data <- load_rois(experiment_folder)
 
}


main <- function() {

  
  experiment_folder <- "/learnmem_data/results/be979e46217f3a5ec0f254245eb68da5/ANTORTJIM-LAPTOP/2020-06-07_17-31-58/"

  roi_data <- load_rois(experiment_folder)
  cross_data <- rbind(
    gather_cross_data(roi_data, border = 10, side = 1),
    gather_cross_data(roi_data, border = 10, side = -1)
  )
  
  controller_data <- load_controller(experiment_folder)
  
  controller_data <- map(
    c("LED_R_LEFT", "LED_R_RIGHT"),
    ~cbind(
      prepare_shape_data(
        controller_data = controller_data,
        hardware = .
      ),
    hardware = .
    )
  ) %>%
    do.call(rbind, .) %>%
    mutate(t_ms = t * 1000)
  
  
  
  rects <- controller_data %>%
    group_by(hardware) %>%
    group_split() %>%
    map(~scale_shape(., roi_data)) %>%
    map(~add_shape(.))
  
  p <- iplot(roi_data)
  
  for (rect in rects) {
    p <- p + rect
  }
  
  p
  
  p + geom_point(
    data = 
  )
  
}
