#' Parse the region_id from the id
#' 
#' @importFrom purrr map map_chr
#' @import magrittr
parse_region_id <- function(id) {
  map(
    id, ~strsplit(., split = "\\|") %>%
      map_chr(~.[[2]])
  ) %>%
    as.integer
}

# regionid_from_id(roi_data$id)

