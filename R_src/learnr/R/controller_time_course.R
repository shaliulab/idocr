library(data.table)
library(ggplot2)
csv_file <- "/learnmem_data/results/be979e46217f3a5ec0f254245eb68da5/LEARNMEMORY_350/2020-05-18_13-55-16/2020-05-18_13-55-16_learnmem_be979e46217f3a5ec0f254245eb68da5.csv"

controller_time_course <- function(csv_file) {
  DT <- data.table::fread(csv_file)
  
  DT.melt <- melt(DT, id.vars = c("V1", "t"), variable.name = "hardware")
  
  p <- ggplot(data = DT.melt, aes(y = t, x = value)) +
    geom_point(size = 0.02) +
    facet_wrap("hardware")
  return(p)
}

p <- controller_time_course(csv_file)
p
