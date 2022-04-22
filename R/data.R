#' An IDOC dataset of 20 animals and 12 minutes of controller
#'
#' A dataset containing the position of 20 animals over 11 minutes of recording
#' as well as the status of all IDOC stimulus components over time
#'
#' @format A list with entries roi_map, var_map, metadata, tracker, controller
#' \describe{
#'   \item{tracker}{data.table with position, distance traveled and time for all animals}
#'   \item{controller}{data.table with status of each stimulus component over time}
#'   \item{roi_map}{position of top left corner, width and height of each ROI}
#'   \item{var_map}{detailed description of the columns provided in the tracker dataset}
#'   \item{metadata}{information about the experiment (when, which version of software, etc)}
#'   ...
#' }
"toy_dataset"