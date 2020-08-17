library(idocr)
<<<<<<< HEAD
setwd('/1TB/Cloud/Data/idoc_data/results/7eb8e224bdb944a68825986bc70de6b1/IDOC_001')
p1 <- idocr(experiment_folder = "2020-07-17_16-31-46", #select the experement folder
           border = 5, min_exits_required = 3, hardware = c('TREATMENT_A_LEFT', 'TREATMENT_A_RIGHT', 'TREATMENT_B_LEFT', 'TREATMENT_B_RIGHT'))
p1 + ggtitle(label = '2020-07-17-16-31-46', subtitle = 'Treatment a is X')
export_summary(experiment_folder = '2020-07-17_16-31-46', output_csv = '~/test.csv')
=======
experiment_folder <- "/idoc_data/results/7eb8e224bdb944a68825986bc70de6b1/IDOC_001/2020-07-17_15-01-10/2020-07-17_15-01-10_7/"
p5 <- idocr(experiment_folder = experiment_folder, border = 10, min_exits_required = 3,
            hardware = c('ODOR_A_LEFT', 'ODOR_A_RIGHT'))

p5$gg
>>>>>>> 30292f50c07ba577d21d582115b1cc570e0bf146
