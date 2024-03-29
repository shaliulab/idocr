#' @export
#' @importFrom parallel mclapply
#' @param delay Apply a time offset to the treatment time series
#' to account for the time it takes for odour to arrive to the chamber. Units in seconds
main <- function(experiment_folder, Test, analysis_mask, experimenter, experiment_type, CS_plus, concentration, US_Volt_pulses, Food, Incubator_Light, Genotype,mc.cores=1, partition="IDOC_RESULTS_TEMP", decision_zones=5:10, delay=2) {
    
  if (substr(experiment_folder, 1, 1) != "/") {
      root <- Sys.getenv(partition)
      if (root == "") {
        warning(paste0(partition, " not found"))
      }
      experiment_folder <- file.path(root, experiment_folder)
    }
  
    for (mask_name in names(analysis_mask)) {
      analysis_mask[[mask_name]] <- analysis_mask[[mask_name]] + delay
    }

    nrow <- 1
    ncol <- 20
    plot_height <- 15
    plot_width <- 25

  #################################Folders#############################
  

  #################################experimenter#############################
  
  # Change the name of the labels as you please
  # the first label should match treatment_A on your paradigm
  # the second label should match treatment_B on your paradigm
  labels <- c("OCT", "AIR")
  CSplus_idx <- 1 # or 2 depending on   which treatment is CS+
  
  # leave this empty or fill something relevant for the experiment
  # it will appear in the subtitle of the plot
  # (below the big title)

  # Minimal number of exits required to consider the data
  # of one animal significant and then compute a index from it
  min_exits_required <- 3

  
  #### Probably you dont want to change this
  #### Please change these numbers only if you know what you are doing
  
  # Behavioral masking
  # Ignore exits happening this amount of seconds
  # after the previous exit
  # to avoid counting the same exit 
  # as two exits happening within ridiculously little time  
  mask_duration <- 1
  
  # Analysis mask
  # This is a list of numeric vectors of length 2
  # The name of the vector should represent some block or interval of your experiment
  # i.e. pre conditioning, post conditioning, etc
  # The vector should delimit the start and end time of the block in seconds
  # Passing this argument to idocr() will cause R to generate a subfolder
  # in the experiment data folder, for each element in the list
  # The folder will have the name of the element in the list
  # e.g. this list will create a subfolder called EVENT1 and another called EVENT2
  # Each of them will contain a pdf and png version of the plot but only the interval
  # when the mask is active is analyzed. It is marked accordingly on the plot
  # Moreover, you get SUMMARY and PI .csv files
  
  
  parallel::mclapply(X=decision_zones, mc.cores = mc.cores, FUN = function(border_mm) {
    
    names(analysis_mask) <- c(
      paste0(Test, "_GLOBAL_", border_mm, "mm"),
      paste0(Test, "_1_", border_mm, "mm"),
      paste0(Test, "_2_", border_mm, "mm")
    )
    ##################################################
    # CAUTION!! DONT CHANGE ANY CODE BELOW THIS LINE
    ##################################################
    
    treatments <- c(
      "TREATMENT_A",
      "TREATMENT_B"
    )
    
    src_file <- rstudioapi::getActiveDocumentContext()$path
    outputs <- idocr(
      experiment_folder = experiment_folder,
      treatments = treatments,
      border_mm = border_mm,
      min_exits_required = min_exits_required,
      src_file = src_file,
      subtitle = paste0(experimenter,"_",experiment_type, ", ", CS_plus, ", ", concentration, " & ", US_Volt_pulses, ", ", Genotype , ", ",Food, ", ", Incubator_Light),
      delay = delay, CSplus_idx = CSplus_idx,
      mask_duration = mask_duration,
      analysis_mask = analysis_mask,
      labels = labels,
      nrow=nrow, ncol=ncol,
      height=plot_height, width=plot_width
    )
    invisible(NULL)
  })
}


