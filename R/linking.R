#' Find the raw data for an experiment in an IDOC database
#' The found folder is saved as a new column of the metadata called idoc_folder
#' metadata must be a data frame with columns:
#' * Files: the basename of the IDOC folder (without the parent folder)
#'
#' result_dir must be a directory with the following structure:
#' One folder for every month whene at least one experiment was done. The folder is called YYYY-MM-idoc_data
#' Inside the month folders, there must be one subfolder for every experiment group
# The subfolder must contain then a 'subsubfolder' for every IDOC session performed.
#' Example
#' result_dir
#'  |
#'  |--- 2022-01-idoc_data
#'             |--- 2022-01-10_13-00-00 (FOO_STM)
#'                      |--- 2022-01-10_13-00-00
#'                         |--- 2022-01-10_13-10-00
#'                         |--- 2022-01-10_13-20-00
#'             |--- 2022-01-10_14-00-00 (BAR_STM)
#'                         |--- 2022-01-10_14-00-00
#'                         |--- 2022-01-10_14-10-00
#'                         |--- 2022-01-10_14-20-00
#'  |--- 2022-02-idoc_data
#'             |--- 2022-02-12_13-00-00 (FOO)
#'                         |---
#'                         |---
#'                         |---
#'             |--- 2022-02-13_14-00-00 (BAR)
#'                         |---
#'                         |---
#'                         |---
#' @export
#' @import data.table
link_idoc_metadata <- function(metadata, result_dir, verbose = TRUE) {
  if (!("sheet" %in% colnames(metadata))) {
    metadata$sheet <- ""
  }
  metadata <- data.table::copy(metadata[!is.na(PRE_ROI) & PRE_ROI != "NA", ])
  metadata <- data.table::copy(metadata[!is.na(POST_ROI) & POST_ROI != "NA", ])
  metadata <- metadata[order(sheet, Files), ]
  metadata[, folder__ := Files]
  metadata[, sheet__ := sheet]
  metadata_unique <- metadata[, .SD[1], by = .(Files, sheet)]
  metadata_unique$idoc_folder <- NA_character_

  metadata_unique <- metadata_unique[, link_idoc_file(.SD, result_dir = result_dir, verbose = verbose), by = .(Files, sheet)]
  metadata_linked <- merge(metadata, metadata_unique[, .(Files, sheet, idoc_folder)], by = c("Files", "sheet"))
  metadata_linked[, fly_name_reference := paste0(Files, "_ROI_", PRE_ROI)]

  return(metadata_linked)
}

#' @import data.table
link_idoc_file <- function(metadata, result_dir, verbose = FALSE) {
  year <- substr(metadata$folder__, 1, 4)
  month <- substr(metadata$folder__, 6, 7)
  month_folder <- paste0(year, "-", month, "-idoc_data")
  month_folder <- file.path(result_dir, month_folder)
  experiments_of_the_month <- list.files(month_folder, full.names = TRUE)
  hits <- c()
  for (folder in experiments_of_the_month) {
    if (metadata$folder__ == basename(folder)) {
      hits <- c(folder)
      break
    }
  }

  out <- data.table::copy(metadata)

  if (length(hits) == 1) {
    if (verbose) {
      message(paste0("1 hit found for ", metadata$sheet_, "/", metadata$folder__))
    }
    out[, idoc_folder := hits[1]]
  } else if (length(hits) == 0) {
    warning(paste0("0 hits found for ", metadata$sheet_, "/", metadata$folder__))
    out[, idoc_folder := NA_character_]
  } else {
    warning(paste0(length(hits), " hits found for ", metadata$sheet_, "/", metadata$folder__))
    print(metadata[, .(sheet__, folder__)])
    print(paste0(metadata$folder__, ": ", paste0(hits, collapse = ", ")))
    out[, idoc_folder := NA_character_]
  }
  return(out)
}
