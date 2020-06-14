
# main(experiment_folder ='/1TB/Cloud/Data/idoc_data/results/7eb8e224bdb944a68825986bc70de6b1/FLYSLEEPLAB_SETUP/2020-06-10_17-42-08', old_mapping = TRUE, plot_basename = '2020-06-10_17-42-08')
# main(experiment_folder = '/1TB/Cloud/Data/idoc_data/results/7eb8e224bdb944a68825986bc70de6b1/FLYSLEEPLAB_SETUP/2020-06-10_17-48-53/', old_mapping = TRUE, plot_basename = '2020-06-10_17-48-53')
p1 <- main(experiment_folder = '/1TB/Cloud/Data/idoc_data/results/FLYSLEEPLAB_SETUP/2020-06-12_13-27-08', border = 10, min_exits_required = 3)
p2 <- main(experiment_folder = '/1TB/Cloud/Data/idoc_data/results/FLYSLEEPLAB_SETUP/2020-06-12_13-51-46', border = 10, min_exits_required = 3)
p3 <- main(experiment_folder = "/1TB/Cloud/Data/idoc_data/results/FLYSLEEPLAB_SETUP/2020-06-12_15-00-24", border = 10, min_exits_required = 3)
cowplot::plot_grid(p1, p2, nrow = 2)
p4 <- main(experiment_folder = "/1TB/Cloud/Data/idoc_data/results/FLYSLEEPLAB_SETUP/2020-06-12_19-40-37/", border = 10, min_exits_required = 3, hardware = c('ODOR_A_LEFT', 'ODOR_A_RIGHT'))
