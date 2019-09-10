library(ggplot2)
library(ggvis)
# library(dplyr)
# library(data.table)
library(cowplot)
# library(stringr)
library(LeMDTr)
# Read data
filename <- 'lemdt_results/LeMDTe27SL5a9e19f94de287e28f789825/LEARNER_001/2019-09-10_17-36-19/2019-09-10_17-36-19_LeMDTe27SL5a9e19f94de287e28f789825.csv'
lemdt_result <- na.omit(read.table(file = filename, sep = ',', header = T, stringsAsFactors = F)[,-1])

# clean header rows (bug in cache save adds headers)
# lemdt_result <- lemdt_result[lemdt_result$cx!="cx",]
# lemdt_result$t <- as.numeric(lemdt_result$t)
# lemdt_result$arena <- as.numeric(lemdt_result$arena)
# lemdt_result$cx <- as.integer(lemdt_result$cx)


arena_width <- 125 # pixels
arena_width_mm <- 50 # mm
decision_zone_mm <- 5# mm

# transform from pixels to mm. Assume the whole chamber (125 pixes)
# is 5 mm (50 mm)
lemdt_result$mm <- lemdt_result$cx/arena_width*arena_width_mm
lemdt_result$mm <- lemdt_result$mm + arena_width_mm/2



# Make a data table
lemdt_result <- data.table::as.data.table(lemdt_result)

##################################
## Add period column
##################################

lemdt_result <- add_period_column(lemdt_result)


##################################
## Define periods/blocks
##################################

lemdt_result2 <- define_unique_periods(lemdt_result)
lemdt_result21 <- copy(lemdt_result2)

##################################
## Set a time series frequency  ##
##################################

lemdt_result2 <- set_timeseries_frequency(lemdt_result2)



##################################
## Clean mistracked datapoints
##################################

lemdt_result3 <- clean_mistracked_points(lemdt_result2)
lemdt_result4 <- copy(lemdt_result3)


##################################
## Impute missing datapoints
##################################

lemdt_result5 <- impute_missing_point(lemdt_result3)




p1 <- lemdt_result2 %>% ggplot(., aes(x = t/60, y = mm_mean, group = arena)) + 
  facet_grid(. ~  as.integer(arena)) +
  scale_y_continuous(breaks = c(0, 50), labels = c(0, 5)) +
  geom_point(size=.05) +
  scale_x_continuous(breaks = seq(1, max(lemdt_result$t), 1)) +
  coord_flip() +
  guides(fill = F, col = F)


p2 <- lemdt_result3 %>% ggplot(., aes(x = t/60, y = mm_mean, group = arena)) + 
  facet_grid(. ~  as.integer(arena)) +
  scale_y_continuous(breaks = c(0, 50), labels = c(0, 5)) +
  geom_point(size=.05) +
  scale_x_continuous(breaks = seq(1, max(lemdt_result$t), 1)) +
  coord_flip() +
  guides(fill = F, col = F)



p1


p3 <- lemdt_result5 %>% ggplot(., aes(x = t/60, y = mm_mean, group = arena, col = imputed)) + 
  facet_grid(. ~  as.integer(arena)) +
  scale_y_continuous(breaks = c(0, 50), labels = c(0, 5)) +
  geom_point(size=.05) +
  scale_x_continuous(breaks = seq(1, max(lemdt_result$t), 1)) +
  coord_flip() +
  guides(fill = F, col = F)


##################################
## Compute position L/D/R based on mm
##################################

lemdt_result6 <- compute_side(lemdt_result5)


# rect_data <- data.frame(xmin = c(first_odour_choice_start, first_odour_choice_start, second_odour_choice_start, second_odour_choice_start, third_odour_choice_start, third_odour_choice_start, fourth_odour_choice_start, fourth_odour_choice_start, fifth_odour_choice_start, fifth_odour_choice_start, sixth_odour_choice_start, sixth_odour_choice_start),
#                         xmax = c(first_odour_choice_end, first_odour_choice_end, second_odour_choice_end, second_odour_choice_end, third_odour_choice_end, third_odour_choice_end, fourth_odour_choice_end, fourth_odour_choice_end, fifth_odour_choice_end, fifth_odour_choice_end, sixth_odour_choice_end, sixth_odour_choice_end),
#                         ymin = c(-60, 0, -60, 0), ymax = c(0, 60, 0, 60),
#                         col = c('white', 'black', 'black', 'white'), fill = c('blue', 'white', 'white', 'blue'))

p3 <- plot_trace_with_pin_events(lemdt_result = lemdt_result6)
p3

weird_rows <- time_series[, find_decision_zone_non_traversed(t, pos), by=arena]
weird_rows %>%
  group_by(arena) %>%
  summarise(count = n())



p4 <- plot_grid(
  p1, p2, p3,
  labels = c('Before', 'Clean', 'Imputed'),
  ncol = 3
)
ggsave(plot = p4, filename = "LeMDTe27SL5a9e19f94de287e28f789825/LEARNER_001/2019-08-23_13-13-50/traces.png", height = 10, width = 40)





# ggvis(time_series, x = ~t/60, y=  ~mm)

