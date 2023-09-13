experiments <- list(
  c(experiment_folder= "/Users/FlySleepLab_Dropbox/Antonio/FSLLab/Projects/IDOC/results/IDOC_002/2023-07-07_15-18-53(ET_CCC_20m)/2023-07-07_14-24-07", test="PRE"),
  c(experiment_folder= "/Users/FlySleepLab_Dropbox/Antonio/FSLLab/Projects/IDOC/results/IDOC_002/2023-07-07_15-18-53(ET_CCC_20m)/2023-07-07_15-18-53", test="POST"),
  
  c(experiment_folder=  "/Users/FlySleepLab_Dropbox/Antonio/FSLLab/Projects/IDOC/results/IDOC_002/2023-07-12_14-25-09(ET_spaced_overnight)/2023-07-12_14-25-09", test="PRE"),
  c(experiment_folder= "/Users/FlySleepLab_Dropbox/Antonio/FSLLab/Projects/IDOC/results/IDOC_002/2023-07-12_14-25-09(ET_spaced_overnight)/2023-07-13_15-46-03", test="POST"),
  
  c(experiment_folder=   "/Users/FlySleepLab_Dropbox/Antonio/FSLLab/Projects/IDOC/results/IDOC_002/2023-07-20_16-06-41_AOJ_learning/2023-07-20_16-06-41", test="PRE"),
  c(experiment_folder=   "/Users/FlySleepLab_Dropbox/Antonio/FSLLab/Projects/IDOC/results/IDOC_002/2023-07-20_16-06-41_AOJ_learning/2023-07-20_17-23-28", test="POST"),
  
  c(experiment_folder=   "/Users/FlySleepLab_Dropbox/Antonio/FSLLab/Projects/IDOC/results/IDOC_002/2023-08-03_15-31-27_AOJ_Learning/2023-08-03_15-31-27", test="PRE"),
  c(experiment_folder=   "/Users/FlySleepLab_Dropbox/Antonio/FSLLab/Projects/IDOC/results/IDOC_002/2023-08-03_15-31-27_AOJ_Learning/2023-08-03_16-39-31", test="POST"),

  c(experiment_folder=   "/Users/FlySleepLab_Dropbox/Antonio/FSLLab/Projects/IDOC/results/IDOC_002/2023-08-08_16-14-27_AOJ_learning/2023-08-08_16-14-27", test="PRE"),
  c(experiment_folder=   "/Users/FlySleepLab_Dropbox/Antonio/FSLLab/Projects/IDOC/results/IDOC_002/2023-08-08_16-14-27_AOJ_learning/2023-08-08_17-09-37", test="POST"),
  
  c(experiment_folder=   "/Users/FlySleepLab_Dropbox/Antonio/FSLLab/Projects/IDOC/results/IDOC_002/2023-08-09_13-56-17(ET_LTM_SD)/2023-08-09_13-56-17", test="PRE"),
  c(experiment_folder=   "/Users/FlySleepLab_Dropbox/Antonio/FSLLab/Projects/IDOC/results/IDOC_002/2023-08-09_13-56-17(ET_LTM_SD)/2023-08-10_18-44-21", test="POST"),

  c(experiment_folder=  "/Users/FlySleepLab_Dropbox/Antonio/FSLLab/Projects/IDOC/results/IDOC_002/2023-08-16_14-15-36(ET_LTM_SD)/2023-08-16_14-15-36", test="PRE"),
  c(experiment_folder= "/Users/FlySleepLab_Dropbox/Antonio/FSLLab/Projects/IDOC/results/IDOC_002/2023-08-16_14-15-36(ET_LTM_SD)/2023-08-17_16-57-15", test="POST"),

  c(experiment_folder=  "/Users/FlySleepLab_Dropbox/Antonio/FSLLab/Projects/IDOC/results/IDOC_002/2023-08-17_14-45-53(ET_LTM_SD)/2023-08-17_14-45-53", test="PRE"),
  c(experiment_folder=  "/Users/FlySleepLab_Dropbox/Antonio/FSLLab/Projects/IDOC/results/IDOC_002/2023-08-17_14-45-53(ET_LTM_SD)/2023-08-18_18-16-51", test="POST"),

  c(experiment_folder=  "/Users/FlySleepLab_Dropbox/Antonio/FSLLab/Projects/IDOC/results/IDOC_002/2023-08-21_15-02-37(ET_LTM_SD)/2023-08-21_15-02-37", test="PRE"),
  c(experiment_folder=  "/Users/FlySleepLab_Dropbox/Antonio/FSLLab/Projects/IDOC/results/IDOC_002/2023-08-21_15-02-37(ET_LTM_SD)/2023-08-22_17-06-10", test="POST"),

  c(experiment_folder= "/Users/FlySleepLab_Dropbox/Antonio/FSLLab/Projects/IDOC/results/IDOC_002/2023-08-22_14-26-35(ET_LTM_SD)/2023-08-22_14-26-35", test="PRE"),
  c(experiment_folder=  "/Users/FlySleepLab_Dropbox/Antonio/FSLLab/Projects/IDOC/results/IDOC_002/2023-08-22_14-26-35(ET_LTM_SD)/2023-08-23_17-22-26", test="POST"),

  c(experiment_folder= "/Users/FlySleepLab_Dropbox/Antonio/FSLLab/Projects/IDOC/results/IDOC_002/2023-08-23_15-02-03(ET_LTM_SD)/2023-08-23_15-02-03", test="PRE"),
  c(experiment_folder=  "/Users/FlySleepLab_Dropbox/Antonio/FSLLab/Projects/IDOC/results/IDOC_002/2023-08-23_15-02-03(ET_LTM_SD)/2023-08-24_18-08-55", test="POST")
)

args_list <- lapply(1:length(experiments), function(i) {
  list(
    experiment_folder = experiments[[i]]["experiment_folder"],
    Test = experiments[[i]]["test"],
    analysis_mask <- list(
      global = idocr2::global_mask,
      trial1 = idocr2::trial1,
      trial2 = idocr2::trial2
    ),
    experimenter = "ET",
    experiment_type = "Aversive_Memory_PRE_paired",
    CS_plus = "OCT",
    concentration = "1:500",          
    #US_Volt_pulses = "US = ES_75V 12 pulses 1/4sec_1X"
    US_Volt_pulses = "US = ES_75V 12 pulses 1/4sec_6X",        
    #Food = "ATR+"
    Food = "SA-ATR-",
    Incubator_Light = "Blue",
    Genotype = "Iso31",
    mc.cores=1,
    partition = "IDOC_RESULTS_TEMP",
    decision_zones=7
  )
})

parallel::mclapply(X = args_list[1:2], FUN = function(args) {do.call(idocr2::main, args)}, mc.cores = 1)


lapply(1:length(experiments), function(i) {
  experiment_folder <- experiments[[i]]["experiment_folder"]
  rois <- experiments[[i]]["rois"]
  
  plotting_params <- readRDS(file = file.path(experiment_folder, "POST_GLOBAL_7mm", "plotting_params.rds"))
  
  pi <- plotting_params$analysis$pi[plotting_params$analysis$pi$region_id %in% rois,]
  tracker <- plotting_params$dataset$tracker[plotting_params$dataset$tracker$region_id %in% rois,]
  annotation <- plotting_params$analysis$annotation[plotting_params$analysis$annotation$region_id %in% rois, ]
  return(list(plotting_params=plotting_params, pi=pi, tracker=tracker, annotation=annotation))
})

out <- plot_dataset(
  experiment_folder = NULL,
  dataset = plotting_params$dataset, analysis = plotting_params$analysis, analysis_mask = plotting_params$analysis_mask, result_folder=".",
  downward = TRUE, labels=c("OCT", "AIR"), do_mark_analysis_mask=FALSE, nrow=1, ncol=5
)

out$plot
