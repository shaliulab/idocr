output_path_maker <- function(experiment_folder, suffix, extension='.csv') {
  metadata <- load_metadata(experiment_folder)
  output_csv <- file.path(
    experiment_folder,
    paste0(metadata[metadata$field == 'date_time', "value"],
           "_",
           metadata[metadata$field == 'machine_id', "value"],
           "_",
           suffix,
           extension
    )
  )
}