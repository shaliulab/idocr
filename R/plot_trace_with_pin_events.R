#' @import data.table ggplot2
#' @export
#'
#'  
plot_trace_with_pin_events <- function(lemdt_result, borders, pins_relevant = 1:4, colors=c("red", "blue"), arena_width_mm = 50) {
  
  
  ##################################
  ## Compute preference index
  ##################################
  pindex <- lemdt_result[, .(n = count_exits(position)[[3]],
                    pi = preference_index(position)), by = .(arena, period)]
  
  
  
  lemdt_result <- arrange(lemdt_result, period, period)
  
  rle_period <- rle(lemdt_result$period)
  
  
  rle_period_values_split <- strsplit(rle_period$values, split = "")
  
  relevant <- lapply(rle_period_values_split, function(x) {sum(as.integer(x)[pins_relevant]) == 2}) %>% unlist %>% which
  
  number_different_events <- length(unique(rle_period$values[relevant]))
  
  
  starts <- cumsum(rev(rev(c(1,rle_period$lengths))[-1]))
  time_starts <- lemdt_result[starts, "t"]/60
  ends <- cumsum(rle_period$lengths)
  time_ends <- lemdt_result[ends, "t"]/60
  
  y_mins <- c(0, arena_width_mm/2)
  y_max <- c(arena_width_mm/2, arena_width_mm)
  odours <-  c("A", "B")
  names(colors) <- odours
  
  pin_state_matrix <- do.call(rbind, rle_period_values_split)
  rect_data <- data.frame(xmin=NULL, xmax=NULL, ymin=NULL, ymax=NULL, fill=NULL)


  for (r in relevant) {
    pins_on <- which(as.integer(pin_state_matrix[r,pins_relevant]) == 1)
    t_start <- time_starts[r]
    t_end <- time_ends[r]
    for (p in pins_on)  {
      odour <- odours[as.integer(p < 3)+1]
      color <- colors[odour]
      # side <- "left"
      y_min <- borders[[1]]
      y_max <- arena_width_mm
      if (p %% 2 == 0) {
        # side <- "right"
        y_min <- 0
        y_max <- borders[[2]]
      }

      rect_data <- rbind(rect_data, data.frame(
        xmin = t_start, xmax = t_end, ymin = y_min, ymax = y_max, fill = color
      ))
    }
  }
  

  
  rect_data$fill <- factor(as.character(rect_data$fill), levels = colors)
  
  
  pi_data <- data.frame(period=NULL, arena=NULL, x=NULL, pref_index=NULL)

  for (r in relevant) {
    perd <- rle_period$values[r]
    for (a in unique(lemdt_result$arena)) {
      pi_data <- rbind(pi_data, data.frame(
        period = perd, arena = a,
        x = (time_starts[r] + time_ends[r]) / 2,
        pref_index = pindex[arena == a & period == perd,]$pi))
    }
  }
  
  
  p3 <- ggplot() +
    geom_line(data = lemdt_result, aes(y = mm_mean, x = t/60, group = arena), col = "black") + 
    scale_x_continuous(breaks = seq(0, max(lemdt_result$t/60), 0.5)) +
    scale_fill_discrete(name = "Odour", labels = names(colors)) +
    # guides(fill=F) +
    labs(x = "t (m)", y = "mm") + 
    facet_grid(. ~  arena) +
    theme_bw() +
    geom_hline(yintercept = borders[[1]]) +
    geom_hline(yintercept = borders[[2]])
    
  
  
  p3 <- p3 + theme(panel.spacing = unit(3, "lines"), legend.position = "bottom",  legend.direction = "horizontal")

  if(nrow(rect_data) != 0) p3 <- p3 + geom_rect(
    # data
    data = rect_data,
    # mapping
    aes(
      xmin = xmin, xmax = xmax,
      ymin = ymin, ymax = ymax,
      fill = fill),
    # constant
    alpha = 0.5)

  if(nrow(pi_data) != 0) {
    p3 <- p3 + geom_text(data = pi_data, aes(x = x, label = round(pref_index, digits = 2)), y = 1.15 * arena_width_mm) +
      theme(plot.margin = unit(c(1,3,1,1), "lines")) # This widens the right m
  }
  
  
  exits_dataframe <- get_exits_dataframe(lemdt_result, borders)
  if(nrow(exits_dataframe) > 0) {
    # browser()
    p3 <- p3 + geom_point(data = exits_dataframe, mapping = aes(x = t/60, y = x))
  }
  
  p3 <- p3 + coord_flip(clip = "off")
  
 return(p3)
}

