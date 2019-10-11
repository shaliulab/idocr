#' @import data.table ggplot2 ggnewscale RColorBrewer
#' @export
#'
plot_trace_with_pin_events <- function(lemdt_result, borders, index_dataset, pins_relevant = 1:4, colors=c("red", "blue"), arena_width_mm = 50, A=NULL, B = NULL, elshock_periods = character(), annot_on_side = FALSE) {
 
  if(interactive()) {
    # pins_relevant <- 1:4
    # colors <- c('red','blue')
    # arena_width_mm <- 50
    # A <- 'A'
    # B <- 'B'
    # elshock_periods = character()
    # library(ggplot2)
    # library(LeMDTr)
  }

  # browser()
  # Order data by periods
  lemdt_result <- as.data.table(arrange(lemdt_result, period, period))
  
  
  ## Find which periods should have a rectangle
  # Criterion: more than 100 datapoints from all arenas (to avoid noisy transition states)
  # and more than 1 pin on (i.e. one of the odours on one of the sides is on)
  rle_period <- lemdt_result[,rle(period)]
  relevant_periods <- names(which(table(lemdt_result$period) > 100))
  unique_periods <- unique(lemdt_result$period)
  
  periods_numeric <- 1:length(unique_periods)
  names(periods_numeric) <- unique_periods
  relevant_periods <- periods_numeric[relevant_periods]
  
  # Result
  relevant_periods_with_pins_on <- relevant_periods[
    unlist(lapply(strsplit(names(relevant_periods), split = ''), function(x) sum(as.integer(x[pins_relevant])) != 0))
  ]
  
  ## Find which pins are actually on on such periods
  # Build the list from relevant_periods and not from relevant_periods_with_pins_on
  # so we can access them numerically, for example period 4 occupies position 4 of the list and not pos 1
  list_of_pins_on_per_period <- lapply(strsplit(names(relevant_periods), split = ''), function(x) which(as.integer(x[pins_relevant]) == 1))
           
  
  print('Computing time starts and ends')
  time_starts <- lemdt_result[, .(t = min(t/60)), by = 'period']$t
  time_ends <- lemdt_result[, .(t = max(t/60)), by = 'period']$t
  # View(lemdt_result[period == '10011',])
  
  y_mins <- c(0, arena_width_mm/2)
  y_max <- c(arena_width_mm/2, arena_width_mm)
  
  
  odours <-  c(A, B)
  names(colors) <- odours
  

  
  ########################
  # Prepare rect_data
  ########################

  
  rect_data <- data.frame(xmin=NULL, xmax=NULL, ymin=NULL, ymax=NULL, fill=NULL, annotation=character())


  for (r in relevant_periods_with_pins_on) {
    # pins_on is a numeric vector of length up to the length of pins_relevant
    # the value is the identity of the pins_relevant that are on
    pins_on <- list_of_pins_on_per_period[[r]]
    t_start <- unlist(time_starts[r])
    t_end <- unlist(time_ends[r])
    annotation <- ''
    if(rle_period$values[r] %in% elshock_periods) annotation <- '*'
    
    for (p in pins_on)  {
      odour <- odours[as.integer(p < 3)+1]
      fill <- colors[odour]
      # side <- "left"
      y_min <- borders[[1]]
      y_max <- arena_width_mm
      if (p %% 2 == 0) {
        # side <- "right"
        y_min <- 0
        y_max <- borders[[2]]
      }

      rect_data <- rbind(rect_data, data.frame(
        xmin = t_start, xmax = t_end, ymin = y_min, ymax = y_max, fill = fill,
        annotation = annotation
      ))
    }
  }
  

  
  rect_data$fill <- factor(as.character(rect_data$fill), levels = colors)
  
  
  ########################
  # Prepare preference_index data
  ########################
  
  pi_data <- data.frame(period=NULL, arena=NULL, x=NULL, pref_index=NULL)

  for (r in relevant_periods) {
    perd <- names(relevant_periods)[r]
    print(paste0('period ', perd))
    
    # browser()
    for (a in unique(lemdt_result$arena)) {
      if(a == 0) next
      print(paste0('arena ', a))
      pref_index <- index_dataset[arena == a]
      
      pref_index <- pref_index[(subseting_column),]$V1
      # pref_index <- pref_index[subseting_column == perd,]$V1

      if(length(pref_index) == 0) pref_index <- NA
      
      pi_data <- rbind(pi_data, data.frame(
        period = perd, arena = a,
        x = (unlist(time_starts[r]) + unlist(time_ends[r])) / 2,
        pref_index = pref_index))
    }
  }
  
  
 
  ## Base plot
  
  x_limits <- ceiling(c(0, max(lemdt_result$t/60)*1.08, max(max(lemdt_result$t/60)*1.08+1, max(lemdt_result$t/60)*1.1)))
  y_limits <- c(0, arena_width_mm)
  p3 <- ggplot() +
    geom_line(data = lemdt_result[arena != 0], aes(y = mm_mean, x = t/60, group = arena), col = "black") +
    # geom_point(data = lemdt_result, aes(y = mm_mean, x = t/60, group = arena), col = "black") + 
    # geom_text(data = lemdt_result, aes(y = mm_mean, x = t/60, group = arena, label = position), col = "black") +
    
  
    scale_x_continuous(breaks = seq(x_limits[1], x_limits[3], 5), limits = x_limits[c(1,3)]) +
    scale_y_continuous(breaks = seq(y_limits[1], y_limits[2], 25), limits = y_limits) +
    scale_fill_discrete(name = "Odour", labels = names(colors)) +
    # guides(fill=F) +
    labs(x = "t (m)", y = "mm") + 
    facet_wrap(. ~ arena, nrow = 2) +
    theme_bw() +
    geom_hline(yintercept = borders[[1]]) +
    geom_hline(yintercept = borders[[2]])
  
  print('Created base plot successfully')
  
  ## Add exit points
  exits_dataframe <- get_exits_dataframe(lemdt_result[arena!=0], borders)
  if(nrow(exits_dataframe) > 0) {
    # browser()
    p3 <- p3 + geom_point(data = exits_dataframe, mapping = aes(x = t/60, y = x), col = 'blue')
  }
  
  
  print('Exit points added successfully')
  
  ## Add rectangles
  if(nrow(rect_data) != 0) p3 <- p3 + geom_rect(
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
    alpha = 0.5, size = 3) +
    geom_text(data = rect_data, aes(label = annotation, x = (xmin+xmax)/2),  y = .95 * arena_width_mm) +
    geom_text(data = rect_data, aes(label = annotation, x = (xmin+xmax)/2),  y = .05 * arena_width_mm)


  print('Rectangles added successfully')

  ## Add preference index data
  if(nrow(pi_data) != 0) {
    pi_data$pref_index <- as.character(round(pi_data$pref_index, digits = 2))
    pi_data$pref_index[is.na(pi_data$pref_index)] <- 'NA'
  }
   
  print('Index data preprared successfully')


  # browser()
   if(annot_on_side) {
     p3 <- p3 + geom_text(data = pi_data, aes(x = x, label = pref_index), y = .95 * arena_width_mm, size = 3) + theme(plot.margin = unit(c(1,3,1,1), "lines")) # This widens the right m
   } else {
     pi_data$pref_index_numeric <- as.numeric(pi_data$pref_index)
     myPalette <- colorRampPalette(rev(brewer.pal(11, "Spectral")))

     # print('Check 1')
     # browser()

     p3 <- p3 +
       # ggnewscale::new_scale_fill() +
       geom_label(data = pi_data,
                           aes(
                               label = pref_index
                               # fill = pref_index_numeric
                               ),
                           fontface = 'bold', color = 'black', x =  x_limits[2], y = arena_width_mm/2, size = 5)
     
     # p3 <- p3 + scale_fill_gradientn(colours = myPalette(100), limits = c(-1, +1), name = 'Index')
     # print('Check 2')

   }


  print('Index annotation added successfully')

  p3 <- p3 + coord_flip(clip = "off")


  p3 <- p3 + theme(
      panel.spacing = unit(.25, "lines"),
      legend.position = "bottom",
      legend.direction = "horizontal"
    )
  
 return(p3)
}

