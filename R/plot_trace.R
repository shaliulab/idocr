#' @export
plot_trace <- function(experiment_folder) {
  filename <- list.files(path = experiment_folder, pattern = '_LeMDTe27SL5a9e19f94de287e28f789825.csv')
  lemdt_result <- na.omit(read.table(file = file.path(experiment_folder, filename), sep = ',', header = T, stringsAsFactors = F)[,-1])
  
  # transform from pixels to mm. Assume the whole chamber (125 pixes)
  # is 5 mm (50 mm)
  lemdt_result <- px2mm(lemdt_result)
  
  
  ##################################
  ## Add period column
  ##################################
  lemdt_result <- add_period_column(lemdt_result)
  
  ##################################
  ## Define periods/blocks
  ##################################
  lemdt_result2 <- define_unique_periods(lemdt_result)
  
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
  lemdt_result6 <- compute_side(lemdt_result5)
  
  ##################################
  ## Plot
  #################################
  p <- plot_trace_with_pin_events(lemdt_result = lemdt_result6)
  return(p)
}