library(idocr)

setwd('/1TB/Cloud/Data/idoc_data/results/7eb8e224bdb944a68825986bc70de6b1/IDOC_001')
experiment_folder <- "2020-10-05_13-05-51"
experiment_folder <- "/home/luna.kuleuven.be/u0127714/R/x86_64-pc-linux-gnu-library/3.6/idocr/2020-10-05_13-05-51"
src_file <- rstudioapi::getActiveDocumentContext()$path

p1 <- idocr(experiment_folder = experiment_folder, #select the experement folder
           border = 5, min_exits_required = 3, src_file=src_file, subtitle = 'My subtitle', delay=0
)

export_summary(experiment_folder = experiment_folder)
