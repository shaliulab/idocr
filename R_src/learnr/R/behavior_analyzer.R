#' Process the results of an experiment performed using the FSL learning memory setup
#'
#' @import ggplot2 R6
#' @export
BehaviorAnalyzer <- R6Class(classname = "BehaviorAnalyzer", public = list(
  
  experiment_folder = NULL,
  index_function = NULL,
  decision_zone_mm = NULL,
  min_exits_required = NULL,
  max_time_minutes = NULL,
  annotation = NULL,
  A = NULL,
  B = NULL,
  selected_flies = NULL,
  debug = NULL,
  lemdt_result = NULL,
  index_dataset = NULL,
  paradigm = NULL,
  plot_title = NULL,
  arena_width_mm = NULL,
  arena_width=NULL,
  odour_valves = NULL,
  time_series_frequency = NULL,
  pin_names = NULL,
  pin_relevant = NULL,
  colours = NULL,
  rect_data = NULL,
  t_period = NULL,
  odours = NULL,
  
  #' @param experiment_folder character, path to results folder of an experiment
  #' @param index_function function, returns an satistic based on a character vector of states
  #' @param decision_zone_mm numeric, widht of the decision in mm
  #' @param min_exits_required integer, minimum number of crossing events required to return an index
  #' @param max_time_minutes numeric, drop all data after this amount of time since the start of the recording
  #' @param annotation character, text to write in the top left corner of the plot
  #' @param A character, name of odour in valves connected to bottle A
  #' @param B character, name of odour in valves connected to bottle B
  #' @param selected_flies integer vector, only these `region_id`s will be included in the plot
  initialize = function(experiment_folder, index_function = LeMDTr::preference_index,
                        decision_zone_mm=10, min_exits_required=5, max_time_minutes=Inf,
                        annotation = '', A=NULL, B=NULL, selected_flies = 1:20, debug=FALSE)  {
    
    self$experiment_folder <- experiment_folder
    self$index_function <- index_function
    self$decision_zone_mm <- decision_zone_mm
    self$min_exits_required <- min_exits_required
    self$max_time_minutes <- max_time_minutes
    self$annotation <- annotation
    self$A <- A
    self$B <- B
    self$selected_flies <- selected_flies
    self$debug <- debug
    self$plot_title <- basename(experiment_folder)
    self$lemdt_result <- NULL
    self$index_dataset <- NULL
    self$paradigm <- NULL
    self$arena_width_mm <- 50
    self$arena_width <- 125
    self$pin_names <- c(
      'ODOUR_A_LEFT',  # odour A on the left
      'ODOUR_A_RIGHT', # odour A on the right
      'ODOUR_B_LEFT',  # odour B on the left
      'ODOUR_B_RIGHT',  # odour B on the right
      'EL_SHOCK_RIGHT',
      'EL_SHOCK_LEFT'
    )
    
    self$pin_relevant <- 1:4
    self$odours <- c(A, B)
    colours <- c("orange", "purple")
    names(colours) <- self$odours
    self$colours <- colours
    self$odour_valves <-  self$pin_names[self$pin_relevant]
    
    self$rect_data <- NULL
    self$t_period <- NULL
    
    self$time_series_frequency <- 0.25
    invisible(self)
    
  },
  read_experiment = function() {
    self <- read_experiment(self)
    invisible(self)
  },
  
  px2mm = function() {
    self <- px2mm(self)
    invisible(self)
  },
  
  program_name = function(value) {
    # Find the program_name from the paradigm 
    program_name <- self$paradigm[, .(block = unique(block))]$block %>%
      grep(pattern = 'end', invert = T, value = T) %>%
      grep(pattern = 'startup', invert = T, value = T)
    return(program_name)
    
  },

  borders = function(value) {
    left_border <- (self$arena_width_mm - self$decision_zone_mm) / 2
    right_border <- left_border + self$decision_zone_mm
    return(list(left_border, right_border))
  },
  
  #' Add to lemdt_result a column called period reflecting the state of the odour valves
  #' @importFrom magrittr %>%
  #' @importFrom data.table data.table
  #' @param  periods_dt A data.table with a t column and any amount of binary columns capturing the state of the setup 
  #' @return A data.table with a new column called period summarising the state of all the binary columns in a single character
  #' @export
  add_period_column = function() {
    
    periods_dt <- self$lemdt_result[arena == 0]
    periods_dt <- periods_dt[, c("t", self$odour_valves), with = FALSE]
    
    # Define variable represeting the state of the system
    periods_dt$period <- periods_dt %>%
      .[, -c("t"), with = FALSE] %>%
      apply(., 1, function(x) paste(x, collapse = '')
      )
    
    periods_dt <- periods_dt[, !self$odour_valves, with = FALSE]
    lemdt_result_with_periods <- self$lemdt_result[periods_dt, on = 't']
    self$lemdt_result <- lemdt_result_with_periods
    
    
    invisible(self)
    
  },
  
  
  make_side_independent = function() {
    # Reverse position on blocks of 0110
    # so the analysis can be performed on all testing windows
    # regardless of which side is which smell
    dtab <- self$lemdt_result
    dtab[, odor_test_active :=  period != '0000']
    dtab[,subsetting_column := odor_test_active]
    dtab[, reversed := period == '0110']
    reversed_pos <- c('R' = 'L', 'L' = 'R', 'D' = 'D')
    dtab[,rev_position := position]
    dtab[(reversed), rev_position := reversed_pos[position]]
    dtab[, position := NULL]
    setnames(dtab, "rev_position", "position")
    
    self$lemdt_result <- dtab
    
    invisible(self)
  },
  
  compute_side = function() {
    lemdt_result <- self$lemdt_result
    
    # assign left to everything
    lemdt_result[, position := "L"]
    
    borders <- self$borders()
    left_border <- borders[[1]]
    right_border <- borders[[2]]
   
    # if mm_mean is between borders, assign D (decision zone) 
    lemdt_result[mm_mean >= left_border & mm_mean <= right_border, position := "D"]
    
    # if mm_mean is beyond the right_boder, assign R (right)
    lemdt_result[mm_mean > right_border, position := "R"]
    
    self$lemdt_result <- lemdt_result
    
    invisible(self)
    },
  
  compute_index = function() {
    index_dataset <- self$lemdt_result[ ,  c("value_index", "counts") := self$index_function(pos = position, min_exits_required = self$min_exits_required),
                                        by = .(arena, subsetting_column)
                                        ]
    # Remove unneeded columns
    index_dataset[,c("imputed", "odor_test_active") := NULL]
    self$index_dataset <- index_dataset
    invisible(self)
    
  },
  
  find_period_edge = function(dt, edge = "start", column_name = "period_id") {
    edge_function <- list("start" = min, "end" = max)[[edge]]
    times <- dt[,.(t = edge_function(t/60)), by = column_name]$t
    return(times)
  },
  
  # Create relevant_periods
  ####
  #
  # Relevant periods is a named integer vector
  # Each element is a number corresponding to the position of the period_id in the list of period_ids
  # The name is its character code
  # Only those periods with at least 100 datapoints representing it (counting all flies)
  # should be there
  # Their order follows their chronoligcal appearance
  # NOT ALPHABETIC ORDER!!
  find_relevant_periods = function(column_name = "period_id", min_datapoints = 100) {
    # Keep meaningful period_ids
    x <- self$t_period[, eval(c("t", column_name)), with = F]
    
    rle_period <- rle(x[[column_name]])
    
    rle_period <- data.table(lengths = rle_period$lengths, values = rle_period$values)
    rle_period <- rle_period[lengths > min_datapoints,]
    
    # Encode them from 1 to their amount and give each number a name correspondingly
    relevant_periods <- 1:nrow(rle_period)
    names(relevant_periods) <- rle_period$values
    
    
    invisible(relevant_periods)
  },
  
  
  #' @param lemdt_result A data.table with columns t, period_id
  #' @param elshock Nothing for now
  #' @return A data.table with columns xmin, xmax, ymin, ymax, fill and annotation, fit for geom_rect() and geom_label()
  prepare_rect_data = function(elshock_periods = character()) {
    ## Find which periods should have a rectangle
    # Criterion: more than 100 datapoints from all arenas (to avoid noisy transition states)
    # and more than 1 pin on (i.e. one of the odours on one of the sides is on)
    
    # Start of each period_id
    time_starts <- self$find_period_edge(self$t_period, "start", "period_id")
    # End of each period_id
    time_ends <- self$find_period_edge(self$t_period, "end", "period_id")
    
    y_mins <- c(0, self$arena_width_mm/2)
    y_max <- c(self$arena_width_mm/2, self$arena_width_mm)
    
    rect_data <- data.frame(xmin=numeric(), xmax=numeric(), ymin=integer(), ymax=integer(), fill=character(), annotation=character())
    relevant_periods <- self$find_relevant_periods("period_id")
    periods_matrix <- do.call(rbind, strsplit(names(relevant_periods), split = ''))
    mode(periods_matrix) <- "integer"
    
    ## Find which pins are actually on on such periods
    # Build the list from relevant_periods and not from relevant_periods_with_pins_on
    # so we can access them numerically, for example period 4 occupies position 4 of the list and not pos 1
    list_of_pins_on_per_period <- apply(
      # which pins are ON on each period?
      X = periods_matrix[, self$pin_relevant] == 1,
      MARGIN = 1,
      FUN = which
    )
          
    relevant_periods_with_pins_on <- relevant_periods[apply(
      # which periods have at least 1 relevant pin on?
      X = periods_matrix[, self$pin_relevant],
      MARGIN = 1,
      FUN = sum
      ) > 1]
    
    for (r in relevant_periods_with_pins_on) {
      # pins_on is a numeric vector of length up to the length of pin_relevant
      # the value is the identity of the pin_relevant that are on
      pins_on <- list_of_pins_on_per_period[[r]]
      t_start <- unlist(time_starts[r])
      t_end <- unlist(time_ends[r])
      annotation <- ''
      # if(rle_period$values[r] %in% elshock_periods) annotation <- '*'
      
      for (p in pins_on)  {
        odour <- self$odours[as.integer(p < 3)+1]
        fill <- self$colours[odour]
        # side <- "left"
        y_min <- self$borders()[[1]]
        y_max <- self$arena_width_mm
        if (p %% 2 == 0) {
          # side <- "right"
          y_min <- 0
          y_max <- self$borders()[[2]]
        }
        
        rect_data <- rbind(rect_data, data.frame(
          xmin = t_start, xmax = t_end, ymin = y_min, ymax = y_max, fill = fill,
          annotation = annotation
        ))
      }
    }
    
    # make factor
    rect_data$fill <- factor(as.character(rect_data$fill), levels = self$colours)
    
    self$rect_data <- rect_data
    invisible(self)
    
  },
  ## Add rectangles
  add_rectangles = function(p) {
    
    annotation <- NULL
    rect_data <- self$rect_data
    
    if(nrow(rect_data) != 0) {
      
      rectangles <- geom_rect(
        # data
        data = rect_data,
        # mapping
        aes(
          xmin = xmin, xmax = xmax,
          ymin = ymin, ymax = ymax,
          fill = fill,
          # color = as.character(color),
        ),
        # constant
        alpha = 0.5, size = 3)
      p <- p + rectangles
      p

      # geom_text(data = rect_data, aes(label = annotation, x = (xmin+xmax)/2),  y = .95 * self$arena_width_mm) +
      # geom_text(data = rect_data, aes(label = annotation, x = (xmin+xmax)/2),  y = .05 * self$arena_width_mm)
    }
    print('Rectangles added successfully')
    return(p)
    
    
    
  },
  
  prepare_index_data = function() {
    self$index_dataset <- self$index_dataset[, .(subsetting_column, arena, value_index)][!duplicated(self$index_dataset[, .(subsetting_column, arena, value_index)]),][arena != 0,]
    invisible(self)
    
  },
    
  
  #' @import ggplot2
  #' @importFrom grDevices colorRampPalette
  #' @importFrom data.table as.data.table
  #' @importFrom RColorBrewer brewer.pal
  #' @export
  #'
  plot_trace_with_pin_events = function(annot_on_side = FALSE) {
    
    lemdt_result <- self$lemdt_result
    
    # Order data by periods
    lemdt_result <- as.data.table(arrange(lemdt_result, period, period))
    
    ## Compute where the exits happened
    exits_dataframe <- get_exits_dataframe(lemdt_result[arena!=0], self$borders)
   
    max_t <- max(lemdt_result$t/60) 
    
    x_limits <- ceiling(c(
      # start of X axis of the plot
      0,
      # position of the labels over the x axis
      max_t*1.08,
      # end of X axis on the plot
      max_t*1.1
      )
    )
    y_limits <- c(0, self$arena_width_mm)
    
    p <- ggplot() +
      # add trace of the position of the flies over time
      geom_line(data = lemdt_result[arena != 0], aes(y = mm_mean, x = t/60, group = arena), col = "black") +
     
      # limit the x axis (time) and set a break every minutes  
      scale_x_continuous(breaks = seq(x_limits[1], x_limits[3], 5), limits = x_limits[c(1,3)], name = "t(m)") +
      # limit the y axis (mm_mean) and set a break every 25 mm (i.e. 3 breaks for a chamber of 50 mm)
      scale_y_continuous(breaks = seq(y_limits[1], y_limits[2], 25), limits = y_limits, name = "mm") +
      # Name the fill legend
      scale_fill_discrete(name = "Odour", labels = self$odours) +
      # Facet by arena with two rows
      facet_wrap(. ~ arena, nrow = 2) +
      # Draw lines to represent the decision zone
      geom_hline(yintercept = self$borders()[[1]]) +
      geom_hline(yintercept = self$borders()[[2]])
    
    print('Created base plot successfully')
        
        
    if(nrow(exits_dataframe) > 0) {
      # browser()
      p <- p + geom_point(data = exits_dataframe, mapping = aes(x = t/60, y = x), col = "black") +
        # geom_point(data = exits_dataframe[exits_dataframe$odor_test_active,], mapping = aes(x = t/60, y = x), col = "black") +
        scale_color_manual(values = c("orange", "purple"))
    }
    print('Exit points added successfully')
    
    p
    p <- self$add_rectangles(p)
    p
    
    ## Add preference index data
    if(nrow(self$index_dataset) != 0) {
      self$index_dataset$value_index <- as.character(round(self$index_dataset$value_index, digits = 2))
      self$index_dataset$value_index[is.na(self$index_dataset$value_index)] <- 'NA'
    }
    
    print('Index data preprared successfully')
    
    
    # browser()
    if(annot_on_side) {
      p3 <- p3 + geom_text(data = pi_data, aes(x = x, label = pref_index), y = .95 * self$arena_width_mm, size = 3) + theme(plot.margin = unit(c(1,3,1,1), "lines")) # This widens the right m
    } else {
      self$index_dataset$pref_index_numeric <- as.numeric(self$index_dataset$value_index)
      myPalette <- grDevices::colorRampPalette(rev(RColorBrewer::brewer.pal(11, "Spectral")))
      
      # print('Check 1')
      # browser()
      
      p <- p +
        # ggnewscale::new_scale_fill() +
        geom_label(data = self$index_dataset,
                   aes(
                     label = pref_index_numeric
                     # fill = pref_index_numeric
                   ),
                   fontface = 'bold', color = 'black', x =  x_limits[2], y = self$arena_width_mm/2, size = 5)
      
      # p3 <- p3 + scale_fill_gradientn(colours = myPalette(100), limits = c(-1, +1), name = 'Index')
      # print('Check 2')
      
    }
    
    
    print('Index annotation added successfully')
    
    p <- p + coord_flip(clip = "off")
    
    
    p <- p + theme_bw() + theme(
      panel.spacing = unit(.25, "lines"),
      legend.position = "bottom",
      legend.direction = "horizontal"
    )
    
    p <- p + ggtitle(label = self$plot_title, subtitle = paste(
      '  /  Program:',   self$program_name(),
      '  /  min exits:', self$min_exits_required,
      '  /  decision zone (mm):', self$decision_zone_mm,
      '  /  index:', self$index_function(),
      '  /  ', self$annotation, '\n',
      '- -> ', self$A, ' + -> ', self$B
    )
    )
    
    return(p)
  },
  
  #' @param  periods_dt A data.table with two columns: t and period
  #' @import ggplot2
  #' @export
  events_over_time_plot = function(experiment_folder, period_column = "period") {
    plot_title <- basename(experiment_folder)
    
    rle_periods <- self$t_period[, rle(eval(parse(text = period_column)))]
    
    t_start <- self$t_period[c(1, (cumsum(rle_periods$lengths)+1) %>% rev %>% .[-1] %>% rev)][["t"]]
    t_end <- self$t_period[cumsum(rle_periods$lengths)][["t"]]
    period_value <- rle_periods$values
    events <- data.table(start = t_start, end = t_end, value = period_value)
    events[ ,alpha := ifelse(value != "0000", 1, 0)]
    
    p <- ggplot(data = events, mapping = aes(xmin = start, xmax = end, ymin = 0, ymax = 1, fill = value, alpha=alpha)) +
      geom_rect(color = "black") + guides(alpha=F)
    
    ggsave(file.path(experiment_folder, "events_over_time_plot.png"))
    
  },
  
  run = function() {
    
    # Read data (behavior and metadata like odours)
    self$read_experiment()
    
    # Transform pixel-based measurements to mm
    self$px2mm()
    
    # Add periods summary
    # Adds a new column capturing the state of the setup
    # based on the the odour_valves variable 
    # The column is called period and is unique to each block with the same state
    # because a growing integer is attached on its right side
    self$add_period_column()
    
    
    # Make a uniform timeseries
    # There will be a data point for every arena and block of length self$time_series_frequency that at least has 1 datapoint
    # WARNING Takes a few seconds
    lemdt_result_uniform_frequency <- set_timeseries_frequency(self, freq = self$time_series_frequency)
    
    # Clean the data based on simple heuristics of what is possible for a fly to do in only so much time
    lemdt_result_uniform_frequency_clean <- clean_mistracked_points(lemdt_result_uniform_frequency)
    
    # Impute missing points i.e. imagine where the fly is for all blocks of self$time_series_frequency seconds
    # where the tracker could not find the fly in any frame
    lemdt_result_uniform_frequency_clean_imputed <- impute_missing_point(lemdt_result_uniform_frequency_clean)
    self$lemdt_result <- lemdt_result_uniform_frequency_clean_imputed
    # TODO Needed?
    # lemdt_result_uniform_frequency_clean_imputed[, any(is.na(period))]
    
    # Compute position L/D/R based on mm
    # borders <- compute_borders(decision_zone_mm = decision_zone_mm)
    self$compute_side()
    
    # Flip sides in some datapoints so a global index can be computed
    self$make_side_independent()
    
    
    t_period <- self$lemdt_result
    
    # works
    t_period <- t_period[t_period$arena == 0,]
    # does not work
    # t_period2 <- t_period[arena == 0,]
    # I HAVE NO IDE WHY. IT IS A DATA.TABLE!
    
    t_period <- t_period[,c("t", "period", "period_id")]
    self$t_period <- t_period
    
    # Compute preference index
    self$compute_index()
    
    self$prepare_rect_data()
    self$prepare_index_data()
    
    
    p <- self$plot_trace_with_pin_events()
    
    ggsave(filename = file.path(self$experiment_folder, paste0(self$plot_title, '_LeMDT_1_', self$index_function(), '.pdf')), plot = p, width = 12, height = 8)
    ggsave(filename = file.path(self$experiment_folder, paste0(self$plot_title, '_LeMDT_1_', self$index_function(), '.png')), plot = p, width = 12, height = 8)
    
    self$events_over_time_plot(experiment_folder = self$experiment_folder, period_column = "period")
    
  }
))