library(ggplot2)


base_dir <- '~/VIBFlySleepLab/LeMDT/lemdt_results/LeMDTe27SL5a9e19f94de287e28f789825/LEARNER_001/'
setwd(base_dir)
filename1 <- '2019-06-13_12-10-01/2019-06-13_12-10-01_LeMDTe27SL5a9e19f94de287e28f789825.csv'
filename2 <- '2019-06-13_13-15-25/2019-06-13_13-15-25_LeMDTe27SL5a9e19f94de287e28f789825.csv'
filename3 <- '2019-06-13_14-10-32/2019-06-13_14-10-32_LeMDTe27SL5a9e19f94de287e28f789825.csv'
lemdt_result1 <- read.table(file = filename1, sep = ',', header = T, stringsAsFactors = F)[,-1]
lemdt_result2 <- read.table(file = filename2, sep = ',', header = T, stringsAsFactors = F)[,-1]
lemdt_result3 <- read.table(file = filename3, sep = ',', header = T, stringsAsFactors = F)[,-1]


# lemdt_result <- lemdt_result1
lemdt_result <- rbind(
  cbind(lemdt_result1, rank = 1),
  cbind(lemdt_result2, rank = 2),
  cbind(lemdt_result3, rank = 3)
)

lemdt_result <- lemdt_result[!(lemdt_result[['arena']] == 'arena'),]
lemdt_result$arena <- as.factor(as.integer(lemdt_result$arena))
lemdt_result$t <- as.numeric(lemdt_result$t)
lemdt_result$cx <- as.numeric(lemdt_result$cx)


rect_data <- data.frame(xmin = c(5, 5, 12, 12)*60, xmax = c(7, 7, 14, 14)*60,
                        ymin = c(-40, 0, -40, 0), ymax = c(0, 40, 0, 40),
                        col = c('white', 'black', 'black', 'white'), fill = c('blue', 'white', 'white', 'blue'))



lemdt_result <- lemdt_result[(as.integer(as.character(lemdt_result$arena)) %in% 1:10), ]
# lemdt_result <- lemdt_result[!(as.integer(as.character(lemdt_result$arena)) %in% c(5, 7, 8)), ]

p2 <- ggplot() +
  geom_rect(data = rect_data, aes(xmin = xmin, xmax = xmax, ymin = ymin, ymax = ymax,
                                  fill = fill, color = col),
            alpha = 0.5) +
  geom_line(data = lemdt_result[lemdt_result$t < 15*60, ], aes(y = cx, x = t, group = arena, col = arena)) + 
  # facet_grid(. ~  arena) +
  facet_grid(rank ~  arena) +
  coord_flip() +
  guides(fill = F, col = F)

p2
ggsave(filename = "/media/u0120864/L-drive/GBW-0057_SHLI/SAyED/rplot.png", p1)


