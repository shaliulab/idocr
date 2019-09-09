library(ggplot2)


base_dir <- '~/VIBFlySleepLab/LeMDT/lemdt_results/LeMDTe27SL5a9e19f94de287e28f789825/LEARNER_001/'
setwd(base_dir)
filename <- '2019-08-02_19-29-59/2019-08-02_19-29-59_LeMDTe27SL5a9e19f94de287e28f789825.csv'
lemdt_result <- read.table(file = filename, sep = ',', header = T, stringsAsFactors = F)[,-1]
lemdt_result <- lemdt_result[!(lemdt_result[['arena']] == 'arena'),]
lemdt_result$arena <- as.factor(as.integer(lemdt_result$arena))
lemdt_result$t <- as.numeric(lemdt_result$t)
lemdt_result$cx <- as.numeric(lemdt_result$cx)

# here you can set when do the odour markers start and end in the time dimension
first_odour_choice_start <- 2 # minutes
first_odour_choice_end <- 3 # minutes
second_odour_choice_start <- 5 # minutes
second_odour_choice_end <- 6# minutes
third_odour_choice_start <- 8 # minutes
third_odour_choice_end <- 9 # minutes
fourth_odour_choice_start <- 11 # minutes
fourth_odour_choice_end <- 12# minutes


#ODOUR_B_Co2_RIGHT,2,3,NaN,NaN, 
#ODOUR_A_Wine_LEFT,2,3,NaN,NaN,  

#ODOUR_B_co2_RIGHT,5,6,NaN,NaN,

#ODOUR_B_co2_LEFT,8,9,NaN,NaN,

#ODOUR_A_wine_RIGHT,11,12,NaN,NaN,

#ODOUR_A_wine_LEFT,15,16,NaN,NaN,



rect_data <- data.frame(xmin = c(first_odour_choice_start, first_odour_choice_start, second_odour_choice_start, second_odour_choice_start, third_odour_choice_start, third_odour_choice_start, fourth_odour_choice_start, fourth_odour_choice_start),
                        xmax = c(first_odour_choice_end, first_odour_choice_end, second_odour_choice_end, second_odour_choice_end, third_odour_choice_end, third_odour_choice_end, fourth_odour_choice_end, fourth_odour_choice_end),
                        ymin = c(-60, 0, -60, 0), ymax = c(0, 60, 0, 60),
                        col = c('white', 'black', 'black', 'white'), fill = c('blue', 'white', 'white', 'blue'))



lemdt_result <- lemdt_result[(as.integer(as.character(lemdt_result$arena)) %in% 1:20), ]
#lemdt_result <- lemdt_result[!(as.integer(as.character(lemdt_result$arena)) %in% c(1, 6, 11)), ]

p2 <- ggplot() +
  geom_rect(data = rect_data, aes(xmin = xmin, xmax = xmax, ymin = ymin, ymax = ymax,
                                  fill = fill, color = col),
            alpha = 0.5) +
  geom_line(data = lemdt_result, aes(y = cx, x = t/60, group = arena, col = arena)) + 
  # facet_grid(. ~  arena) +
  facet_grid(. ~  arena) +
  scale_x_continuous(breaks = seq(1, max(lemdt_result$t), 1)) +
  coord_flip() +
  guides(fill = F, col = F)

p2




