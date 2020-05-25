experiment_folder <- '/home/vibflysleep/VIBFlySleep/LeMDT/lemdt_results/2019-10-04_13-02-11'
LeMDTr::preprocess_and_plot(experiment_folder, A = 'air', B = 'MCH', decision_zone_mm = 10, min_exits_required = 5, max_time_minutes = 8, annotation = 'MCH -> 1:2000', index_function = LeMDTr::preference_index)

experiment_folder <- '/home/vibflysleep/VIBFlySleep/LeMDT/lemdt_results/2019-10-04_12-46-49'
LeMDTr::preprocess_and_plot(experiment_folder, A = 'OCT', B = 'MCH', decision_zone_mm = 10, min_exits_required = 5, max_time_minutes = 8, annotation = 'OCT -> 1:1000 MCH -> 1:2000', index_function = LeMDTr::preference_index)

experiment_folder <- '/home/vibflysleep/VIBFlySleep/LeMDT/lemdt_results/2019-10-04_12-25-44'
LeMDTr::preprocess_and_plot(experiment_folder, A = 'air', B = 'ACV', decision_zone_mm = 10, min_exits_required = 5, max_time_minutes = 8, annotation = 'ACV -> 1:100', index_function = LeMDTr::preference_index)


experiment_folder <- '/home/vibflysleep/VIBFlySleep/LeMDT/lemdt_results/2019-10-04_12-16-39'
LeMDTr::preprocess_and_plot(experiment_folder, A = 'air', B = 'ACV', decision_zone_mm = 10, min_exits_required = 5, max_time_minutes = 8, annotation = 'ACV -> 1:1000', index_function = LeMDTr::preference_index)


