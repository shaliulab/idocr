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


eucl_dist <- function(p1, p2) {
  sqrt(sum((p1 - p2)**2))
}


wrap_quotes <- function(x) {
  stopifnot(class(x) == "character")
  paste0('"', x, '"')
}
