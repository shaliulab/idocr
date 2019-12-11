#' Process the results of an experiment performed using the FSL learning memory setup
#'
#' @param experiment_folder character, path to results folder of an experiment
#' @param index_function function, returns an satistic based on a character vector of states
#' @param decision_zone_mm numeric, widht of the decision in mm
#' @param min_exits_required integer, minimum number of crossing events required to return an index
#' @param max_time_minutes numeric, drop all data after this amount of time since the start of the recording
#' @param annotation character, text to write in the top left corner of the plot
#' @param A character, name of odour in valves connected to bottle A
#' @param B character, name of odour in valves connected to bottle B
#' @param selected_flies integer vector, only these `region_id`s will be included in the plot
#' @import ggplot2
#' @export
preprocess_and_plot <- function(experiment_folder, index_function = LeMDTr::preference_index,
                                decision_zone_mm=10, min_exits_required=5, max_time_minutes=Inf,
                                annotation = '', A=NULL, B=NULL, selected_flies = 1:20, debug=FALSE) {

  ## # define experiment name
  ## plot_title <- basename(experiment_folder)
  ## 
  ## # read odors
  ## odors_csv <- file.path(experiment_folder, 'odors.csv')
  ## if (file.exists(odors_csv)) {
  ##   odors_table <- read.table(odors_csv, sep = ',', header=T, stringsAsFactors = F)
  ##   if(is.null(A)) A <- odors_table$odor_A
  ##   if(is.null(B)) B <- odors_table$odor_B
  ## } else {
  ##   if(is.null(A)) A <- "A"
  ##   if(is.null(B)) B <- "B"
  ##   
  ## }
  ## 
  ## # read experiment data
  ## filename <- list.files(path = experiment_folder, pattern = 'LeMDT') %>% grep(pattern = '.csv', x = ., value = T)
  ## file_path <- file.path(experiment_folder, filename)
  ## if (length(file_path) == 0) {
  ##   warning('Provided path to trace file does not exist')
  ##   return(1)
  ## }
  #
  #
  #  
  ## lemdt_result <- na.omit(read.table(file = file_path, sep = ',', header = T, stringsAsFactors = F)[,-1])
  ## lemdt_result <- lemdt_result[lemdt_result$arena %in% c(0, selected_flies),]
  #
  ## transform from pixels to mm. Assume the whole chamber (125 pixels)
  ## is 5 mm (50 mm)
  ## lemdt_result <- px2mm(lemdt_result)
  ## 
  ## 
  ## ##################################
  ## ## Add period column
  ## ##################################
  ## 
  ## # Needed to compute preference index 
  ## periods_dt <- add_period_column(lemdt_result[arena == 0])
  ## events_over_time_plot(periods_dt, experiment_folder)
  ## 
  ## ##################################
  ## ## Define periods/blocks
  ## ##################################
  ## 
  ## # Distinguish rows where the state (i.e. period) is the same but
  ## # they belong to different blocks
  ## # i.e. first time when odourAleft and odourBright
  ## # and the second time (a few minutes after)
  ## periods_dt <- define_unique_periods(periods_dt)
  ## # lemdt_result0 <- copy(lemdt_result)
  ## 
  ## 
  ## 
  ## ##################################
  ## ## Set a time series frequency  ##
  ## ##################################
  ## 
  ## # Simplifies analysis: have all datapoints equally distributeed
  ## # and in a periodic basis
  ## freq <- 0.25
  ## lemdt_result2 <- set_timeseries_frequency(lemdt_result, freq = freq)
  ## periods_dt[, t :=  floor(t/ freq) * freq]
  ## periods_dt <- as.data.table(
  ##   periods_dt %>% group_by(t) %>%
  ##   summarise(
  ##     period = names(table(period))[1],
  ##     period_id = names(table(period_id))[1]
  ##   ))
  ## 
  ##   
  ## lemdt_result <- lemdt_result2[periods_dt, on = 't']
  ## 
  ## 
  ## # table(lemdt_result$arena)
  ## 
  ## ##################################
  ## ## Clean mistracked datapoints
  ## ##################################
  ## lemdt_result <- clean_mistracked_points(lemdt_result)
 
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
    lemdt_result[, odor_test_active := (substr(period,1,4) != '0000')]
    lemdt_result$subsetting_column <- lemdt_result[["odor_test_active"]]
    lemdt_result[, reversed := period == '0110']
    
    reversed_pos <- c('R' = 'L', 'L' = 'R', 'D' = 'D')
    lemdt_result[,rev_position := position]
    lemdt_result[(reversed), rev_position := reversed_pos[position]]
    
    
    
    index_dataset <- lemdt_result[, .(
      V1 = index_function(pos = rev_position, min_exits_required = min_exits_required)[[1]],
      V2 = index_function(pos = rev_position, min_exits_required = min_exits_required)[[2]]
    ), by = .(arena, subsetting_column)]
    
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


  program_name <- tryCatch({
    data.table::fread(file = file.path(experiment_folder, 'paradigm.csv'))[, .(block = unique(block))]$block %>%
    grep(pattern = 'end', invert = T, value = T) %>%
    grep(pattern = 'startup', invert = T, value = T)
  }, error = function(e) {
    warning(e)
    return("")
  })
  
  
  p <- result$p + ggtitle(label = plot_title, subtitle = paste(
    '  /  Program:',   program_name,
    '  /  min exits:', min_exits_required,
    '  /  decision zone (mm):', decision_zone_mm,
    '  /  index:', index_function(),
    '  /  ', annotation, '\n',
    '- -> ',A, ' + -> ', B
    )
  )
  index_dataset <- result$index_dataset
  
  ggsave(filename = file.path(experiment_folder, paste0(plot_title, '_LeMDT_1_', index_function(), '.pdf')), plot = p, width = 12, height = 8)
  ggsave(filename = file.path(experiment_folder, paste0(plot_title, '_LeMDT_1_', index_function(), '.png')), plot = p, width = 12, height = 8)
  return(list(plot = p, index_dataset = index_dataset))
}
