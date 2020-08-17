library(idocr)
setwd('/1TB/Cloud/Data/idoc_data/results/7eb8e224bdb944a68825986bc70de6b1/IDOC_001')
p1 <- idocr(experiment_folder = "2020-07-17_16-31-46", #select the experement folder
           border = 5, min_exits_required = 3, hardware = c('TREATMENT_A_LEFT', 'TREATMENT_A_RIGHT', 'TREATMENT_B_LEFT', 'TREATMENT_B_RIGHT'))
p1 + ggtitle(label = '2020-07-17-16-31-46', subtitle = 'Treatment a is X')
export_summary(experiment_folder = '2020-07-17_16-31-46', output_csv = '~/test.csv')
