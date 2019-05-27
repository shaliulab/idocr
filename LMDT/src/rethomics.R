#read .txt file
library("readr")
library("ggplot2")
library("dplyr")
base_dir <- "/home/antortjim/MEGA/FlySleepLab/LMDT/data"

dt <- read.csv(file.path(base_dir, "store_144649-28032019.csv"))

ggplot(data = dt, mapping = aes(x = timestamp, y = cx / 60)) +
  geom_line() + coord_flip() +
  facet_grid(~arena)

fly1 <- subset(dt, Arena == '1')
fly2 <- subset(dt, Arena == '2')
fly3 <- subset(dt, Arena == '3')

#or (check if this also works for making subset)
fly1 <- dt[Arena == 1]

#make new column with min instead of sec and rename it to Time
dt[,11] <- (dt[,2])/60
names(dt)[c(11)] <- c("Time")

#making the graphs
library(ggplot)
p<-ggplot(dt, aes(x=RelativePosX, y=Time))

#traces of arenas next to each other -- columns
p+geom_point()+facet_grid(~ Arena)
#traces of arenas next to each other -- rows
p+geom_point()+facet_grid(Arena ~.)

#summary for making plot training
p+
  scale_y_reverse()+
  geom_path()+
  facet_grid(~ Arena)+
  annotate("rect", xmin=0, xmax=200, ymin=1, ymax=3, fill="mediumspringgreen", alpha= .2)+
  annotate("rect", xmin=0, xmax=-200, ymin=1, ymax=3, fill="#C42126", alpha= .2)+
  annotate("rect", xmin=-200, xmax=200, ymin=5, ymax=6, fill="mediumspringgreen", alpha= .2)+
  annotate("rect", xmin=-200, xmax=200, ymin=7, ymax=8, fill="#C42126", alpha= .2)+
  annotate("rect", xmin=-200, xmax=200, ymin=10, ymax=11, fill="mediumspringgreen", alpha= .2)+
  annotate("rect", xmin=-200, xmax=200, ymin=12, ymax=13, fill="#C42126", alpha= .2)+
  annotate("rect", xmin=0, xmax=200, ymin=18, ymax=20, fill="#C42126", alpha= .2)+
  annotate("rect", xmin=0, xmax=-200, ymin=18, ymax=20, fill="mediumspringgreen", alpha= .2)+
  theme_classic(base_size=10)+
  theme(axis.title.x=element_blank(),axis.text.x=element_blank(),axis.ticks.x=element_blank())+
  labs(y="time in min")

#summary for making plot test, not switching odors
p+
  scale_y_reverse()+
  geom_path()+
  facet_grid(~ Arena)+
  annotate("rect", xmin=0, xmax=200, ymin=5, ymax=7, fill="#C42126", alpha= .2)+
  annotate("rect", xmin=0, xmax=-200, ymin=5, ymax=7, fill="mediumspringgreen", alpha= .2)

#summary for making plot test, switching odors
p+
  scale_y_reverse()+
  geom_path()+
  facet_grid(~ Arena)+
  annotate("rect", xmin=0, xmax=200, ymin=5, ymax=6, fill="#C42126", alpha= .2)+
  annotate("rect", xmin=0, xmax=-200, ymin=5, ymax=6, fill="mediumspringgreen", alpha= .2)+
  annotate("rect", xmin=0, xmax=200, ymin=6, ymax=7, fill="mediumspringgreen", alpha= .2)+
  annotate("rect", xmin=0, xmax=-200, ymin=6, ymax=7, fill="#C42126", alpha= .2)