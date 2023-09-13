#' Masks representing onset of condtioned stimuli
#'
#'  Each vector represents a time interval (begin, end)
#'  which can be used to exclude any stimuli outside of it
#'  when counting decision zone exits 
#'
#' @export
#' global_mask
global_mask <- c(0, Inf)
#' @export
#' trial1
trial1 <- c(58, 122)
#' @export
#' trial2
trial2 <- c(178, 242)
