#'
#' @importFrom data.table fwrite
#' @export
export_pi <- function(experiment_folder, output_csv) {
  result <- idocr(experiment_folder)
  data.table::fwrite(x = result$pi, file = output_csv)
}