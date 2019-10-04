#' @export
preprocess_and_plot <- function(experiment_folder, decision_zone_mm=10, debug=FALSE, A='A', B='B', min_exits_required=5, max_time_minutes=Inf, annotation = '', index_function = LeMDTr::preference_index) {
  
  # experiment_folder <- '/home/vibflysleep/VIBFlySleep/LeMDT/lemdt_results/2019-10-04_12-46-49/'
  
  # if(interactive()) {
    # decision_zone_mm=10
    # experiment_folder='/home/antortjim/MEGAsync/Gitlab/LeMDT/lemdt_results/LeMDTe27SL5a9e19f94de287e28f789825/LEARNER_001/2019-09-16_17-46-34'
    # experiment_folder = '/home/antortjim/MEGAsync/Gitlab/LeMDT/lemdt_results/LeMDTe27SL5a9e19f94de287e28f789825/LEARNER_001/2019-09-16_16-04-19'
    # experiment_folder = '~/2019-09-17_20-23-18'
   # experiment_folder <- '/home/luna.kuleuven.be/u0120864/2019-09-17_21-05-56'
  
    # }
  filename <- list.files(path = experiment_folder, pattern = '_LeMDTe27SL5a9e19f94de287e28f789825.csv')
  file_path <- file.path(experiment_folder, filename)
  if (length(file_path) == 0) {
    warning('Provided path to trace file does not exist')
    return(1)
  }
  
  lemdt_result <- na.omit(read.table(file = file_path, sep = ',', header = T, stringsAsFactors = F)[,-1])
  lemdt_result <- lemdt_result[lemdt_result$t < max_time_minutes*60,]

  
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
  if (!debug) lemdt_result2 <- lemdt_result2[arena != 0,]
  
  if(nrow(lemdt_result2) == 0) {
    warning('No data collected')
    return(0)
  }
  
  
  elshock_periods <- lemdt_result2[(lemdt_result2$eshock_left + lemdt_result2$eshock_right) > 0,unique(period)]
  
  
  ##################################
  ## Set a time series frequency  ##
  ##################################
  lemdt_result2 <- set_timeseries_frequency(lemdt_result2)
  
  ##################################
  ## Clean mistracked datapoints
  ##################################
  lemdt_result3 <- clean_mistracked_points(lemdt_result2)
  table(lemdt_result3$period)
  
  
  borders <- compute_borders(decision_zone_mm = decision_zone_mm)
  
  ##################################
  ## Impute missing datapoints
  ##################################
  result <- tryCatch({
    lemdt_result5 <- impute_missing_point(lemdt_result3)
    table(lemdt_result5$period)
    
    ##################################
    ## Compute position L/D/R based on mm
    ##################################
    lemdt_result6 <- compute_side(lemdt_result5, borders, decision_zone_mm=decision_zone_mm)
    table(lemdt_result6$period)
    
    
    ##################################
    ## Compute preference index
    ##################################
    lemdt_result <- lemdt_result6
    # browser()
    # p <- '01101'
    # lemdt_result[arena == a & period == p, position]
    # 
    # for (i in 1:length(unique(lemdt_result$arena))) {
    #   for (j in 1:length(unique(lemdt_result$period))) {
    #     a <- unique(lemdt_result$arena)[i]
    #     p <- unique(lemdt_result$period)[j]
    #     res <- index_function(lemdt_result[arena == a & period == p, position], min_exits_required = min_exits_required)
    #     print(a)
    #     print(p)
    #     print(res)
    #   }
    # }
    # browser()
    index_dataset <- lemdt_result[, .(
      V1 = index_function(pos = position, min_exits_required = min_exits_required)[[1]],
      V2 = index_function(pos = position, min_exits_required = min_exits_required)[[2]]
    ), by = .(arena, period)]
    
    p <- plot_trace_with_pin_events(lemdt_result = lemdt_result, borders=borders, index_dataset = index_dataset, A=A,B=B, elshock_periods = elshock_periods)
    
    
    
    result <- list(p = p, index_dataset = index_dataset)
    result
    
   }, error = function(e) {
      message(e)
      if(debug) {
        index_dataset <- data.table(n = 0, V1 = NA, V2 = NA, arena = 0, period = "00001")
        lemdt_result6 <- compute_side(lemdt_result3, borders, decision_zone_mm=decision_zone_mm)
        p <- plot_trace_with_pin_events(lemdt_result = lemdt_result6, borders=borders, index_dataset = index_dataset, A=A,B=B)
        result <- list(p = p, index_dataset = index_dataset)
        result 
      } else(
        return(0)
      )
      
    })
  
  title <- basename(experiment_folder)
  
  program_name <- data.table::fread(file = file.path(experiment_folder, 'paradigm.csv'))[, .(block = unique(block))]$block %>%
    grep(pattern = 'end', invert = T, value = T) %>%
    grep(pattern = 'startup', invert = T, value = T)
  
  p <- result$p + ggtitle(label = title, subtitle = paste(
    '  /  Program:',   program_name,
    '  /  min exits:', min_exits_required,
    '  /  decision zone (mm):', decision_zone_mm,
    '  /  index:', index_function(),
    '  /  ', annotation))
  index_dataset <- result$index_dataset
  ggsave(filename = file.path(experiment_folder, paste0(index_function(), '.pdf')), plot = p, width = 12, height = 8)
  ggsave(filename = file.path(experiment_folder, paste0(index_function(), '.png')), plot = p, width = 12, height = 8)
  
  ##################################
  ## Plot
  #################################
  
  print(filename)
  
  return(list(plot = p, index_dataset = index_dataset))
}
