#' @export
preprocess_and_plot <- function(experiment_folder, decision_zone_mm=10) {
 
  # if(interactive()) {
    decision_zone_mm=10
    # experiment_folder='/home/antortjim/MEGAsync/Gitlab/LeMDT/lemdt_results/LeMDTe27SL5a9e19f94de287e28f789825/LEARNER_001/2019-09-16_17-46-34'
    experiment_folder = '/home/antortjim/MEGAsync/Gitlab/LeMDT/lemdt_results/LeMDTe27SL5a9e19f94de287e28f789825/LEARNER_001/2019-09-16_16-04-19'
  # }
  filename <- list.files(path = experiment_folder, pattern = '_LeMDTe27SL5a9e19f94de287e28f789825.csv')
  
  file_path <- file.path(experiment_folder, filename)
  if (length(file_path) == 0) {
    warning('Provided path to trace file does not exist')
    return(1)
  }
  
  lemdt_result <- na.omit(read.table(file = file_path, sep = ',', header = T, stringsAsFactors = F)[,-1])
  
  # transform from pixels to mm. Assume the whole chamber (125 pixes)
  # is 5 mm (50 mm)
  lemdt_result <- px2mm(lemdt_result)
  
  
  ##################################
  ## Add period column
  ##################################
  lemdt_result <- add_period_column(lemdt_result)
  table(lemdt_result$period)
  ##################################
  ## Define periods/blocks
  ##################################
  lemdt_result2 <- define_unique_periods(lemdt_result)
  lemdt_result2 <- lemdt_result2[arena != 0,]
  
  ##################################
  ## Set a time series frequency  ##
  ##################################
  lemdt_result2 <- set_timeseries_frequency(lemdt_result2)
  
  ##################################
  ## Clean mistracked datapoints
  ##################################
  lemdt_result3 <- clean_mistracked_points(lemdt_result2)
  
  ##################################
  ## Impute missing datapoints
  ##################################
  lemdt_result5 <- impute_missing_point(lemdt_result3)
  
  ##################################
  ## Compute position L/D/R based on mm
  ##################################
  borders <- compute_borders(decision_zone_mm = decision_zone_mm)
  lemdt_result6 <- compute_side(lemdt_result5, borders, decision_zone_mm=decision_zone_mm)
  
  
  ##################################
  ## Compute preference index
  ##################################
  lemdt_result <- lemdt_result6
  # browser()
  pindex <- lemdt_result[, .(
    n = count_exits(position)[[3]],
    pi = preference_index(position)
    ), by = .(arena, period)]
 
  
  ##################################
  ## Plot
  #################################
  p <- plot_trace_with_pin_events(lemdt_result = lemdt_result, borders=borders, pindex = pindex)
  
  return(list(plot = p, preference_index = pindex))
}
