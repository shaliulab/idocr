#' Generate a toy dataset for testing purposes

#' Rebound movement if the animal hits the minimum of maximum of the dimension
#' 
#' Useful so movement magnitude is not lost due to wall efect
#' @param x Current position on either dimension (length 1)
#' @param minn Minimum value on that dimension
#' @param maxx Maximum value on that dimension
#' @return Corrected position with min/max offset rebounded into allowed bounds 
rebound <- function(x, minn, maxx) {
  stopifnot(minn < maxx)
  x <- x - max(0, (x - maxx)) * 2
  x <- x - min(0, (x - minn)) * 2
  return(x)
}

walk_x <- function(x, minn, maxx, sd_x) {

  if (x > (minn + 1/5*(maxx-minn)) & x < (minn + 4/5*(maxx-minn)))
    random_walk(sd_x)
  else
    beta_walk(x, minn, maxx)
}

beta_walk <- function(x, minn=0, maxx=200, scaler=2) {
  scaler * (stats::rbeta(
    n = 1,
    shape1 = 5 * (maxx-x-minn) / (maxx-minn),
    shape2 = 5 * (x-minn) / (maxx - minn)) - 0.5
  )
}


random_walk <- function(sd_x) {
  stats::rnorm(n = 1, mean = 0, sd = sd_x)
}


#' Brownian motion on the 2d space
#' 
#' @param start_pos numeric vector of length 2 with current position of animal in x and y coords
#' @param quiescent Whether the fly can walk (FALSE) or not (TRUE)
#' @param sd_y standard deviation of the normal distribution governing the movement on y
walk <- function(start_pos, quiescent=FALSE, sd_y=0.5) {
  
  if (quiescent) {
    movement <- c(0, 0)
  } else {
    movement <- c(
      walk_x(start_pos[1], 0, 200, 3),
      stats::rnorm(n = 1, mean = 0, sd = sd_y)
    )
  }

  next_pos <- round(start_pos + movement)
  # make sure no negative
  next_pos <- c(rebound(next_pos[1], 0, 200), rebound(next_pos[2], 0, 30))
  distt <- eucl_dist(next_pos, start_pos)
  next_pos[3] <- distt
  
  return(next_pos)
}


#' Generate a toy fly movement dataset
#' 
#' @param steps Number of timepoints in toy dataset
#' @param p Probability of a quiescent fly i.e. p chance that the simulated
#' fly does not move at all
#' @param ... extra arguments to walk
#' @importFrom data.table as.data.table
toy_roi <- function(steps=100, p=0.2, ...) {
  
  if (stats::runif(n = 1) < p) {
    quiescent <- TRUE
  } else {
    quiescent <- FALSE
  }
  header <- "id,x,y,w,h,phi,xy_dist_log10x1000,is_inferred,has_interacted,frame_count,t"
  
  cols <- unlist(strsplit(header, ","))
  
  ncols <- 3
  positions <- matrix(rep(0, ncols*steps), nrow=steps, ncol=ncols)
  colnames(positions) <- c("x", "y", "dist")
  positions[1,] <- c(100, 15, 0)
  
  for (i in 2:steps) {
    positions[i,] <- walk(positions[i-1, 1:2], quiescent, ...)
  }
  
  roi_data <- cbind(positions, id = 0)
  roi_data <- cbind(roi_data, phi = 100)
  roi_data <- cbind(roi_data, w = 7)
  roi_data <- cbind(roi_data, h = 7)
  roi_data <- cbind(roi_data, is_inferred = 0)
  roi_data <- cbind(roi_data, has_interacted = 0)
  roi_data <- cbind(roi_data, xy_dist_log10x1000 = 0)
  roi_data[, "xy_dist_log10x1000"] = log10(roi_data[, "dist"]+0.003) * 1000
  roi_data <- cbind(roi_data, frame_count = 1:nrow(roi_data))
  roi_data <- cbind(roi_data, t = 1:nrow(roi_data) / 9)
  return(data.table::as.data.table(roi_data[,cols]))
}


#' Generate a multi animal dataset
#' 
#' Call toy_roi as many times as channels are passed
#' @param channels Number of animals to simulate
#' @param ... Extra arguments to [toy_roi()]
#' @seealso [toy_roi()]
toy_roi_all <- function(channels=20, ...) {
  
  rois <- lapply(1:channels, function(i) {message("ROI_", i); toy_roi(...)})
  names(rois) <- paste0("ROI_", 1:20)
  return(rois)
}
  

#' Generate a toy controller dataset based on a paradigm
#' 
#' @importFrom janitor row_to_names
#' @importFrom dplyr do
#' @importFrom magrittr `%>%`
#' @param paradigm data.table with format stimulus, start, off
#' @return data.table with one column per stimulus in paradigm
#' and one row per sampling timepoint. The value of the i,j cell
#' states whether the ith stimulus was on at time j
toy_controller <- function(paradigm=NULL) {
  
  . <- NULL
  
  get_status <- function(paradigm, t) {
    
    paradigm %>%
      dplyr::do(
        data.frame(stimulus = .$stimulus, status = ifelse(.$on < t & .$off > t, 1, 0))
      ) %>%
      t %>%
      janitor::row_to_names(row_number = 1, .) %>%
      cbind(., t  = t)
  }
  
  if (!is.null(paradigm)) {
      controller_data <- lapply(seq(from = 0, to = 360, by = 0.5), function(t) {
      get_status(paradigm, t)
    }) %>% do.call(rbind, .) %>%
      apply(., 2, as.numeric)
  } else
    controller_data <- data.table()
  
  return(controller_data)
}


#' Generate a toy metadata table
#' @return data.table with a toy metadata
get_metadata <- function() {
  
  field <- value <- . <- NULL
  
  machine_id <- paste(rep(0, 32), collapse="")
  datetime <- "2021-01-01_01-01-01"
  machine_name <- "IDOC_001"
  run_id <- paste0(datetime, "_", substr(x = machine_id, start = 1, stop = 5))
  git_version <- "7439aff4b8b48675f992648e8ffc5af564bbff7e"
  
  metadata <- data.table(
    field = c(
      "run_id", "machine_id", "machine_name", "version", "date_time",
      "selected_options", "settings", "user_data", "description"
    ),
    value = c(
      run_id, machine_id, machine_name,
      paste0("{'id': ", git_version, ", 'date': ", datetime, "}"),
      datetime,
      "{}", "{}", "{}", ""
    )
  )
  
  c("version", "selected_options", "settings", "user_data") %>%
    lapply(., function(f) {
      val <- metadata[field == f, value]
      metadata[field == f, value := wrap_quotes(val)]
    })
  
  return(metadata)
}


get_roi_map <- function(channels=20) {
  
  tlx <- rep(c(337, 537), each=10)
  tly <- rep(79 + (0:9) * 30, times=2)
  roi_map <- data.table(x=tlx, y=tly, w=182, h=40, value=1:20, idx=1:20)
  return(roi_map)

}


#' Save a dataset to a .csv database
#' A .csv database is a collection of .csv files under the same folder
#' where every .csv file has a common prefix and a differential key
#' that distinguishes it from other files and hints at its contents
#' @param dataset A list with entries metadata, roi_data,
#' controller_data, var_map and roi_map
#' @param dest A folder where to generate a .csv database.
#' Created on the spot if it doesn't exist
#' @importFrom data.table fwrite
#' @importFrom purrr imap
#' @return NULL
write_dataset <- function(dataset, dest) {
  
  dir.create(dest, recursive = TRUE, showWarnings = F)
  
  purrr::imap(
    dataset$roi_data,
    ~data.table::fwrite(
      x = .x,
      file = file.path(dest, build_filename(dataset$metadata, .y)),
      row.names = T, quote = F
    )
  )
  
  data.table::fwrite(
    x = dataset$metadata,
    file = file.path(dest, build_filename(dataset$metadata, "METADATA")),
    row.names = T, quote = F
  )
  data.table::fwrite(
    x = dataset$roi_map,
    file = file.path(dest,  build_filename(dataset$metadata, "ROI_MAP")),
    row.names = T, quote = F
  )
  data.table::fwrite(
    x = dataset$var_map,
    file = file.path(dest, build_filename(dataset$metadata, "VAR_MAP")),
    row.names = T, quote = F
  )
  data.table::fwrite(
    x = dataset$controller_data,
    file = file.path(dest,  build_filename(dataset$metadata, "CONTROLLER_EVENTS")),
    row.names = T, quote = F
  )
}


#' Generate a toy dataset
#' 
#' @param dest Path to the destination folder where toy dataset should be stored
#' It is created if not available
#' @param paradigm data.table containing a paradigm i.e. a list of controller events 
#' @param ...  Additional arguments for toy_roi_all
#' @export
#' @seealso toy_roi_all
#' @seealso toy_controller
generate_toy_dataset <- function(dest=NULL, paradigm=NULL, ...) {
  
  roi_data <- toy_roi_all(channels=20, ...)
  controller_data <- toy_controller(paradigm)
  
  roi_map <- get_roi_map(channels=20)

  var_map <- data.table(
    var_name = c("x", "y", "w", "h", "phi",
                 "xy_dist_log10x1000", "is_inferred", "has_interacted",
                 "frame_count"),
    sql_type = c("SMALLINT", "SMALLINT", "SMALLINT", "SMALLINT",
                 "SMALLINT", "SMALLINT", "BOOLEAN", "SMALLINT", "INT"),
    functional_type = c("distance", "distance", "distance", "distance",
                        "angle", "relative_distance_1e6",
                        "bool", "interaction", "count")
  )
  
  metadata <- get_metadata()
  dataset <- list(
    roi_data = roi_data, roi_map = roi_map, var_map = var_map,
    metadata = metadata, controller_data = controller_data
  )
  
  if (!is.null(dest)) write_dataset(dataset, dest)
  
  dataset$tracker <- do.call(rbind, 
          lapply(1:length(dataset$roi_data), function(i) {
            cbind(dataset$roi_data[[i]], region_id=i)
          })
  )
  
  dataset$controller <- as.data.table(dataset$controller_data)
  dataset$controller_data <- NULL
  dataset$roi_data <- NULL
  
  return(dataset)
}


toy_tracker_small <- function() {
  tracker_data <- data.table::data.table(
    id = rep(c("toy|01", "toy|02"), each = 20),
    region_id = rep(c(1, 2), each=20),
    x = c(
      #roi1
      0, 0, 0, 0,
      # cross left
      -3, -5, -3, -5, -7,
      # cross in
      0,
      # cross right
      3,
      # cross in
      0,
      # cross right
      4,
      # cross in
      0,
      # cross left
      -5, 
      # cross in
      0,
      # cross right
      5, 3,
      #roi2
      0, 0, 0, 0, 0, 0, 0, 0, 2, 0, 0,
      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
    ),
    t  = c(1:20, 1:20)
  )
}


toy_controller_small <- function() {
  controller_data <- data.table::data.table(
    TREATMENT_A_LEFT = c(0, 1, 1, 0, 0, 0),
    TREATMENT_B_RIGHT = c(0, 1, 1, 0, 0, 0),
    TREATMENT_A_RIGHT = c(0, 0, 0, 1, 1, 0),
    TREATMENT_B_LEFT = c(0, 0, 0, 1, 1, 0),
    t = 0:5
  )
}


toy_dataset_small <- function() {
  dataset <- list(
    tracker = toy_tracker_small(),
    controller = toy_controller_small(),
    limits = c(-100, 0, 100), border = 5,
    treatments = LETTERS[1:2],
    stimuli = paste0(rep(c("TREATMENT_A", "TREATMENT_B"), each=2), c("_LEFT", "_RIGHT")),
    CSplus = "TREATMENT_A", CSminus = "TREATMENT_B"
  )
  return(dataset)
}


toy_cross_data <- function() {
  rbind(
    tibble::tibble(
      id = "toy|01", region_id=1, t=c(2, 5), side = 1
    ),
    tibble::tibble(
      id = "toy|01", region_id=1, t=c(6, 7, 8), side = -1
    )
  )
}


toy_event_data <- function() {
  tibble::tibble(
    stimulus = "TREATMENT_A_LEFT", t_start = 1000, t_end = 3000, 
    side = 1, idx=0, treatment="TREATMENT_A"
  )
}


toy_annotation_data <- function() {
  annotation_data <- tibble::tibble(
    id = "toy|01", region_id = 1, t = 1:10, idx = 0, 
    side = c(1,1,1,-1,-1,1,1,1,1,1)
  )
  
  annotation_data$type <- c("appetitive", "aversive")[
    ifelse(annotation_data$side > 0, annotation_data$side, annotation_data$side+3)
  ]
  annotation_data
}

toy_rectangle_data <- function() {
  
  crossing_data <- toy_annotation_data()
  tracker_data <- toy_tracker_small()
  controller_data <- toy_controller_small()
  
  dataset <- list(
    controller = controller_data,
    stimuli = colnames(controller_data)[1:4],
    limits = c(-100, 100),
    tracker = NA
  )
  
  rectangles <- define_rectangle_all(dataset)
  return(rectangles)
}

toy_pi_data <- function() {
  set.seed(2021)
  pi <- data.frame(
    region_id=1:20,
    appetitive=round(stats::runif(20,0,5), digits = 0),
    aversive=round(stats::runif(20,0,5), digits = 0),
    preference_index = stats::runif(20, min=-1, max=1)
  )
  return(pi)
}
