library(ggplot2)


lemdt_result1 <- read.table('VIBFlySleepLab/LeMDT/lemdt_results/LeMDTe27SL5a9e19f94de287e28f789825/LEARNER_001/2019-06-11_22-42-54/2019-06-11_22-42-54_LeMDTe27SL5a9e19f94de287e28f789825.csv', sep = ',', header = T, stringsAsFactors = F)[,-1]
lemdt_result2 <- read.table('VIBFlySleepLab/LeMDT/lemdt_results/LeMDTe27SL5a9e19f94de287e28f789825/LEARNER_001/2019-06-11_22-58-16/2019-06-11_22-58-16_LeMDTe27SL5a9e19f94de287e28f789825.csv', sep = ',', header = T, stringsAsFactors = F)[,-1]
lemdt_result <- rbind(cbind(lemdt_result1, pressure = 100), cbind(lemdt_result2, pressure = 150))
lemdt_result <- lemdt_result[!(lemdt_result[['arena']] == 'arena'),]
lemdt_result$arena <- as.factor(as.integer(lemdt_result$arena))
lemdt_result$t <- as.numeric(lemdt_result$t)
lemdt_result$cx <- as.numeric(lemdt_result$cx)


rect_data <- data.frame(xmin = c(5, 5, 12, 12)*60, xmax = c(7, 7, 14, 14)*60,
                        ymin = c(-40, 0, -40, 0), ymax = c(0, 40, 0, 40), fill = c('blue', 'red', 'red', 'blue'))



lemdt_result <- lemdt_result[!(as.integer(as.character(lemdt_result$arena)) %in% c(5, 7, 8)), ]

p1 <- ggplot() +
  geom_rect(data = rect_data, aes(xmin = xmin, xmax = xmax, ymin = ymin, ymax = ymax, fill = fill),
            alpha = 0.5) +
  geom_line(data = lemdt_result[lemdt_result$t < 15*60, ], aes(y = cx, x = t, group = arena, col = arena)) + 
  facet_grid(pressure ~  arena) +
  scale_y_reverse() + coord_flip() +
  guides(fill = F, col = F)

p1
ggsave(filename = "/media/u0120864/L-drive/GBW-0057_SHLI/SAyED/rplot.png", p1)


