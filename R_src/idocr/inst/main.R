library(idocr)
experiment_folder <- "/idoc_data/results/7eb8e224bdb944a68825986bc70de6b1/IDOC_001/2020-07-17_15-01-10/2020-07-17_15-01-10_7/"
p5 <- idocr(experiment_folder = experiment_folder, border = 10, min_exits_required = 3,
            hardware = c('ODOR_A_LEFT', 'ODOR_A_RIGHT'))

p5$gg
