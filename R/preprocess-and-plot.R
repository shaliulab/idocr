#' @export
preprocess_and_plot <- function(experiment_folder, decision_zone_mm=10, debug=FALSE, A='A', B='B', min_exits_required=5, max_time_minutes=Inf, annotation = '', index_function = LeMDTr::preference_index) {

  # if(interactive()) {
    # decision_zone_mm=10
    # # # experiment_folder='/home/antortjim/MEGAsync/Gitlab/LeMDT/lemdt_results/LeMDTe27SL5a9e19f94de287e28f789825/LEARNER_001/2019-09-16_17-46-34'
    # experiment_folder <- '/home/antortjim/MEGAsync/setup_results/2019-10-04_13-02-11'
    # index_function <- LeMDTr::preference_index
    # min_exits_required <- 5
    # max_time_minutes <- Inf
    # A <- 'A'
    # B <- 'B'
    # debug = F
    # annotation <- ''
    # experiment_folder = '/home/antortjim/MEGAsync/Gitlab/LeMDT/lemdt_results/LeMDTe27SL5a9e19f94de287e28f789825/LEARNER_001/2019-09-16_16-04-19'
  # }
  filename <- list.files(path = experiment_folder, pattern = '_LeMDTe27SL5a9e19f94de287e28f789825.csv')
  
  file_path <- file.path(experiment_folder, filename)
  if (length(file_path) == 0) {
    warning('Provided path to trace file does not exist')
    return(1)
  }
  
  lemdt_result <- na.omit(read.table(file = file_path, sep = ',', header = T, stringsAsFactors = F)[,-1])
  
  # transform from pixels to mm. Assume the whole chamber (125 pixels)
  # is 5 mm (50 mm)
  lemdt_result <- px2mm(lemdt_result)
  
  
  ##################################
  ## Add period column
  ##################################

  # Needed to compute preference index 
  periods_dt <- add_period_column(lemdt_result[arena == 0])[,c("t", "period")]
  
  
  ##################################
  ## Define periods/blocks
  ##################################
  
  # Distinguish rows where the state (i.e. period) is the same but
  # they belong to different blocks
  # i.e. first time when odourAleft and odourBright
  # and the second time (a few minutes after)
  periods_dt <- define_unique_periods(periods_dt)
  # lemdt_result0 <- copy(lemdt_result)
  
  
  
  ##################################
  ## Set a time series frequency  ##
  ##################################
  
  # Simplifies analysis: have all datapoints equally distributeed
  # and in a periodic basis
  freq <- 0.25
  lemdt_result2 <- set_timeseries_frequency(lemdt_result, freq = freq)
  periods_dt[, t :=  floor(t/ freq) * freq]
  periods_dt <- as.data.table(
    periods_dt %>% group_by(t) %>%
    summarise(
      period = names(table(period))[1],
      period_id = names(table(period_id))[1]
    ))
  
    
  lemdt_result <- lemdt_result2[periods_dt, on = 't']
  
  
  table(lemdt_result$arena)
  
  ##################################
  ## Clean mistracked datapoints
  ##################################
  lemdt_result <- clean_mistracked_points(lemdt_result)
 
  ##################################
  ## Impute missing datapoints
  ##################################
  result <- tryCatch({
    
    
    lemdt_result <- impute_missing_point(lemdt_result)
    
    lemdt_result[, any(is.na(period))]
    
    ##################################
    ## Compute position L/D/R based on mm
    ##################################
    borders <- compute_borders(decision_zone_mm = decision_zone_mm)
    lemdt_result <- compute_side(lemdt_result, borders, decision_zone_mm=decision_zone_mm)
    
    
    ##################################
    ## Compute preference index
    ##################################
    # lemdt_result <- lemdt_result6
    # browser()
    
    # lemdt_result[, any_pin_on := F]
    lemdt_result[, any_pin_on := (substr(period,1,4) != '0000')]
    lemdt_result$subseting_column <- lemdt_result[["any_pin_on"]]
    # if()
    lemdt_result[, reversed := period == '0110']
    
    reversed_pos <- c('R' = 'L', 'L' = 'R', 'D' = 'D')
    lemdt_result[(reversed), position := reversed_pos[position]]
    
    
    index_dataset <- lemdt_result[, .(
      V1 = index_function(pos = position, min_exits_required = min_exits_required)[[1]],
      V2 = index_function(pos = position, min_exits_required = min_exits_required)[[2]]
    ), by = .(arena, subseting_column)]
    
    p <- plot_trace_with_pin_events(lemdt_result = lemdt_result, borders=borders, index_dataset = index_dataset, A=A,B=B)
    
    
    
    result <- list(p = p, index_dataset = index_dataset)
    result
    
  }, error = function(e) {
  message(e)
  if(debug) {
    index_dataset <- data.table(n = 0, V1 = NA, V2 = NA, arena = 0, period = "00001")
    lemdt_result <- compute_side(lemdt_result, borders, decision_zone_mm=decision_zone_mm)
    p <- plot_trace_with_pin_events(lemdt_result = lemdt_result, borders=borders, index_dataset = index_dataset, A=A,B=B)
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
return(list(plot = p, index_dataset = index_dataset))
}
