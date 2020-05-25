#! /usr/bin/Rscript

library(optparse)

option_list <- list( 
  # make_option(c("-v", "--verbose"), action="store_true", default=TRUE,
              # help="Print extra output [default]"),
  # make_option(c("-q", "--quietly"), action="store_false", 
              # dest="verbose", help="Print little output"),
  make_option(c("-e", "--experiment_folder"), type = 'character' )
)

# get command line options, if help option encountered print help and exit,
# otherwise if options not found on command line then set defaults, 
opt <- parse_args(OptionParser(option_list=option_list))
# experiment_folder <- 'lemdt_results/LeMDTe27SL5a9e19f94de287e28f789825/LEARNER_001/2019-09-11_10-50-53/'
experiment_folder <- opt$experiment_folder

result <- LeMDTr::preprocess_and_plot(experiment_folder = experiment_folder)
p <- result$plot
pindex <- result$preference_index

output_plot_path <- file.path(experiment_folder, "trace_plot.png")
output_pindex_path <- file.path(experiment_folder, "pindex.csv")
ggplot2::ggsave(filename = output_plot_path, plot = p)
data.table::fwrite(x = pindex, file = output_pindex_path)

