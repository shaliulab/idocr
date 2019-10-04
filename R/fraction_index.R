#' Compute the fraction of time spent in the right side for each period
#'
#' @param pos A character vector encoding the position of the fly in the chamber (L/D/R)
#' @param min_required Number of exits required to compute the index
#'
#' @return Numeric ranging 0-1 0 shows total aversion for odour on right side, and 1 total preference. -1 is return if min_required is not reached
#' @importFrom stringr str_count
#' @export
#'
#' @examples
#' pos <- c('L','L','L','D','D','D','L','L',"L",'D','D','R','R','R','D')
#' preference_index(pos)
fraction_index <- function(pos=NULL, min_exits_required=NA, min_length=10) {
  
  if(is.null(pos)) {
    return('fraction_index')
  }
  if(length(pos) < min_length)
    return(NA_real_)
  
  fi <- sum(pos == 'R') / (sum(pos == 'R') + sum(pos == 'L'))
  
  return(list(fi, NA))
}
