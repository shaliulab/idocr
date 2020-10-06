library(idocr)

setwd('/1TB/Cloud/Data/idoc_data/results/7eb8e224bdb944a68825986bc70de6b1/IDOC_001')
experiment_folder <- "2020-10-05_13-05-51"
experiment_folder <- "~/R/x86_64-pc-linux-gnu-library/3.6/idocr/2020-10-05_13-05-51"
src_file <- rstudioapi::getActiveDocumentContext()$path

# change what treatment A and B are
# to fit it to your needs
treatment_A <- "OCT"
treatment_B <- "MCH"
treatments <- c(
  TREATMENT_A = treatment_A,
  TREATMENT_B = treatment_B
)


# leave it empty or fill something relevant for the experiment
# it will appear in the subtitle of the plot
# (below the big title)
description <- ""

p1 <- idocr(experiment_folder = experiment_folder, #select the experiment folder
            treatments = treatments,
            border = 5, # mm from the center of the chamber to the decision zone,
            min_exits_required = 3,
            src_file = src_file,
            subtitle = description,
            delay = 0, # seconds offset,
            mask_duration = 0.5 # mask behavior this amount of seconds after an exit,
            # to avoid counting the same exit twice as two exits that happen within ridiculously little time  
            )

export_summary(experiment_folder = experiment_folder)
