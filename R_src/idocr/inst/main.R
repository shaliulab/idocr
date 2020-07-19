<<<<<<< HEAD:R_src/idocr/inst/main.R
# main(experiment_folder ='/1TB/Cloud/Data/idoc_data/results/7eb8e224bdb944a68825986bc70de6b1/FLYSLEEPLAB_SETUP/2020-06-10_17-42-08', old_mapping = TRUE, plot_basename = '2020-06-10_17-42-08')
# main(experiment_folder = '/1TB/Cloud/Data/idoc_data/results/7eb8e224bdb944a68825986bc70de6b1/FLYSLEEPLAB_SETUP/2020-06-10_17-48-53/', old_mapping = TRUE, plot_basename = '2020-06-10_17-48-53')
p1 <- main(experiment_folder = '/1TB/Cloud/Data/idoc_data/results/FLYSLEEPLAB_SETUP/2020-06-12_13-27-08', border = 10, min_exits_required = 3)
p2 <- main(experiment_folder = '/1TB/Cloud/Data/idoc_data/results/FLYSLEEPLAB_SETUP/2020-06-12_13-51-46', border = 10, min_exits_required = 3)
p3 <- main(experiment_folder = "/1TB/Cloud/Data/idoc_data/results/FLYSLEEPLAB_SETUP/2020-06-12_15-00-24", border = 10, min_exits_required = 3)
cowplot::plot_grid(p1, p2, nrow = 2)
p4 <- main(experiment_folder = "/1TB/Cloud/Data/idoc_data/results/FLYSLEEPLAB_SETUP/2020-06-12_19-40-37/", border = 10, min_exits_required = 3, hardware = c('ODOR_A_LEFT', 'ODOR_A_RIGHT'))

experiment_folder <- system.file(
  "idoc_data/results//7eb8e224bdb944a68825986bc70de6b1/IDOC_001/2020-07-17_15-01-10/2020-07-17_15-01-10_7/",
  package = "idocr"
) 
p5 <- main(experiment_folder = experiment_folder, border = 10, min_exits_required = 3, hardware = c('ODOR_A_LEFT', 'ODOR_A_RIGHT'))
=======
library(idocr)
setwd('/1TB/Cloud/Data/idoc_data/results/7eb8e224bdb944a68825986bc70de6b1/IDOC_001')
p1 <- idocr(experiment_folder = "2020-06-12_19-40-37", #select the experement folder
           border = 5, min_exits_required = 3, hardware = c('LED_R_LEFT', 'LED_R_RIGHT'))
p1
export_summary(experiment_folder = '2020-06-12_19-40-37')
>>>>>>> 8fe749edff7dd4142b6d03e5023e4f9ed239d4a0:R_src/idocr/idocr/inst/main.R
