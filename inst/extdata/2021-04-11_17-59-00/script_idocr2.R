# library(idocr2)

##############################################
# CHANGE CODE BELOW THIS LINE
##############################################

#### Probably you want to change this

# Supply an experiment contained in the working directory
# Press TAB to autocomplete
experiment_folder <- "inst/extdata/2021-04-11_17-59-00/"

# Change the name of the labels as you please
# the first label should match treatment_A on your paradigm
# the second label should match treatment_B on your paradigm
labels <- c("OCT", "MCH+ES")
CSplus_idx <- 1 # or 2 depending on which treatment is CS+

# leave this empty or fill something relevant for the experiment
# it will appear in the subtitle of the plot
# (below the big title)
description <- "Enter a description here"

# Minimal number of exits required to consider the data
# of one animal significant and then compute a index from it
min_exits_required <- 3

# Apply a time offset to the treatment time series
# to account for the time it takes for odour to
# arrive to the chambers
# Units in seconds
delay <- 5


#### Probably you dont want to change this
#### Please change these numbers only if you know what you are doing

# Define a distance from the center of the chamber
# to the decision zone
# Units in mm
border_mm <- 5

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
analysis_mask <- list(
  GLOBAL = c(0, Inf),
  PRE_1 = c(60, 120) + delay,
  PRE_2 = c(120, 240) + delay,
  POST_2 = c(1020, 1080) + delay
)   

nrow <- 1
ncol <- 20
height <- 14
width <- 25

##################################################
# CAUTION!! DONT CHANGE ANY CODE BELOW THIS LINE
##################################################

treatments <- c(
  "TREATMENT_A",
  "TREATMENT_B"
)

src_file <- rstudioapi::getActiveDocumentContext()$path

p1 <- idocr(experiment_folder = experiment_folder,
            treatments = treatments,
            border_mm = border_mm,
            min_exits_required = min_exits_required,
            src_file = src_file,
            subtitle = description,
            delay = delay, CSplus_idx = CSplus_idx,
            mask_duration = mask_duration,
            analysis_mask = analysis_mask,
            labels = labels,
            nrow=nrow,ncol=ncol,height=height,width=width
            )
