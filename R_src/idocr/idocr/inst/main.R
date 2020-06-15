library(idocr)
setwd('/1TB/Cloud/Data/idoc_data/results/7eb8e224bdb944a68825986bc70de6b1/IDOC_001')
p1 <- idocr(experiment_folder = "2020-06-12_19-40-37", #select the experement folder
           border = 5, min_exits_required = 3, hardware = c('LED_R_LEFT', 'LED_R_RIGHT'))
p1
export_summary(experiment_folder = '2020-06-12_19-40-37')