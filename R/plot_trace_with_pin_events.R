#' @import data.table ggplot2
#' @export
#'
#'  
plot_trace_with_pin_events <- function(lemdt_result, borders, index_dataset, pins_relevant = 1:4, colors=c("red", "blue"), arena_width_mm = 50, A='A', B = 'B', elshock_periods = character()) {
  
  if(interactive()) {
    pins_relevant <- 1:4
    colors <- c('red','blue')
    arena_width_mm <- 50
    library(ggplot2)
    library(LeMDTr)
  }

  lemdt_result <- as.data.table(arrange(lemdt_result, period, period))
  
  rle_period <- rle(lemdt_result$period)
  
  
  rle_period_values_split <- strsplit(rle_period$values, split = "")
  names(rle_period_values_split) <- unlist(lapply(rle_period_values_split, function(x) paste(x, collapse = '')))
  rle_period_values_split <- rle_period_values_split[unique(rle_period$values)]
  
  rle_period_values_split_unique <- lapply(rle_period_values_split, function(x) {
      as.integer(x)
    }) %>% unique
  
  
  relevant_periods <- rle_period_values_split_unique %>%
      lapply(function(x) sum(x[pins_relevant]) %in% c(2,0)) %>% unlist %>% which
  
  
  number_different_events <- length(unique(rle_period_values_split_unique[relevant_periods]))
  
  
  starts <- cumsum(rev(rev(c(1,rle_period$lengths))[-1]))
  time_starts <- lemdt_result[starts, "t"]/60
  ends <- cumsum(rle_period$lengths)
  time_ends <- lemdt_result[ends, "t"]/60
  
  y_mins <- c(0, arena_width_mm/2)
  y_max <- c(arena_width_mm/2, arena_width_mm)
  odours <-  c(A, B)
  names(colors) <- odours
  
  pin_state_matrix <- do.call(rbind, rle_period_values_split)
  
  
  ########################
  # Prepare rect_data
  ########################

  
  rect_data <- data.frame(xmin=NULL, xmax=NULL, ymin=NULL, ymax=NULL, fill=NULL, annotation=character())


  for (r in relevant_periods) {
    pins_on <- which(as.integer(pin_state_matrix[r,pins_relevant]) == 1)
    t_start <- unlist(time_starts[r])
    t_end <- unlist(time_ends[r,])
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
    perd <- rle_period$values[r]
    print(paste0('period ', perd))
    
    # browser()
    for (a in unique(lemdt_result$arena)) {
      print(paste0('arena ', a))
      pref_index <- index_dataset[arena == a & period == perd,]$V1
      if(length(pref_index) == 0) pref_index <- NA
      
      pi_data <- rbind(pi_data, data.frame(
        period = perd, arena = a,
        x = (unlist(time_starts[r]) + unlist(time_ends[r])) / 2,
        pref_index = pref_index))
    }
  }
  
  
 
  ## Base plot
  
  p3 <- ggplot() +
    geom_line(data = lemdt_result, aes(y = mm_mean, x = t/60, group = arena), col = "black") +
    # geom_point(data = lemdt_result, aes(y = mm_mean, x = t/60, group = arena), col = "black") + 
    # geom_text(data = lemdt_result, aes(y = mm_mean, x = t/60, group = arena, label = position), col = "black") +
    
    
    scale_x_continuous(breaks = seq(0, max(lemdt_result$t/60), 0.5)) +
    scale_fill_discrete(name = "Odour", labels = names(colors)) +
    # guides(fill=F) +
    labs(x = "t (m)", y = "mm") + 
    facet_wrap(. ~ arena, nrow = 2) +
    theme_bw() +
    geom_hline(yintercept = borders[[1]]) +
    geom_hline(yintercept = borders[[2]]) +
    scale_x_continuous(breaks = round(seq(0, max(lemdt_result$t)/60, by = 0.5), digits=3))
  
  ## Add exit points
  exits_dataframe <- get_exits_dataframe(lemdt_result, borders)
  if(nrow(exits_dataframe) > 0) {
    # browser()
    p3 <- p3 + geom_point(data = exits_dataframe, mapping = aes(x = t/60, y = x), col = 'blue')
  }
  p3
  
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
  
  ## Add preference index data
  if(nrow(pi_data) != 0) {
    pi_data$pref_index <- as.character(round(pi_data$pref_index, digits = 2))
    pi_data$pref_index[is.na(pi_data$pref_index)] <- 'NA'
    
    p3 <- p3 + geom_text(data = pi_data, aes(x = x, label = pref_index), y = .95 * arena_width_mm, size = 3) +
      theme(plot.margin = unit(c(1,3,1,1), "lines")) # This widens the right m
  }
  
  p3 <- p3 + coord_flip(clip = "off")  + theme(
    panel.spacing = unit(3, "lines"),
    legend.position = "bottom",
    legend.direction = "horizontal"
    )
  
 return(p3)
}

