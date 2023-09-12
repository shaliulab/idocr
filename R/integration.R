#' @import data.table
#' @import behavr
#' @import sleepr
#' @import ggprism
#' @import ggplot2
#' @importFrom stringr str_pad
make_outputs <- function(dt, variable, folder, prefix) {
  
  # make trace plot using variable    
  dt$target__ <- dt[[variable]]
  bout_dt <- behavr::rejoin(sleepr::bout_analysis(data = dt, var=target__))[, .(id, global_id, duration, t)]
  rejoined <- behavr::rejoin(dt)
  
  gg <- ggplot(data=rejoined, aes(x=t,y=target__)) +
    geom_pop_etho() +
    stat_ld_annotations(color=NA, height=1, alpha=0.2)+scale_x_hours() +
    facet_grid(global_id ~ .) +
    ggtitle(folder)
  
  if (variable=="asleep") {
    gg <- gg + scale_y_continuous(breaks=c(0, 1))
  } else if (variable == "interactions") {
    print("")
  }
  gg <- gg +
    theme(strip.text.y = element_text(angle = 0)) +
    labs(y = variable)
  
  
  # produce summary statistics of var for each interval
  dt_timeseries <- rejoined[, .(global_id, t, target__ = round(target__, 3))] 
  dts <- lapply(intervals, function(interval) {
    d <- data.table::as.data.table(dt_timeseries[t >= behavr::hours(interval[1]) & t < behavr::hours(interval[2]), .(target__ = sum(target__) * 30), by=global_id]) 
    colnames(d)[colnames(d) == "target__"] <- variable
    
    colnames(d)[2] <- paste0(paste0(variable, "_ZT"), stringr::str_pad(interval[1], width = 2, pad = "0"), "-ZT", stringr::str_pad(string = interval[2], width=2, pad="0"))
    d
  })
  dt_summ_events <- Reduce(f = function(x, y) {merge(x, y, by="global_id",  all.x = TRUE, all.y=TRUE)}, x = dts)
  
  
  # make summary statistics of provided bouts
  dts <- lapply(intervals, function(interval) {
    d <- data.table::as.data.table(bout_dt[t >= behavr::hours(interval[1]) & t < behavr::hours(interval[2]), .(duration = round(mean(duration/60), 2)), by=global_id])        
    colnames(d)[2] <- paste0("bout-duration_ZT", stringr::str_pad(interval[1], width = 2, pad = "0"), "-ZT", stringr::str_pad(string = interval[2], width=2, pad="0"))
    d
  })                  
  dt_summ_duration <- Reduce(f = function(x, y) {merge(x, y, by="global_id", all.x = TRUE, all.y=TRUE)}, x = dts)
  
  # merge both summary statistics. For each interval we get
  # 1) residence time as given by variable
  # 2) length of its bouts
  dt_summ <- merge(dt_summ_events, dt_summ_duration, by="global_id")
  
  
  # export trace as csv as well
  dt_timeseries <- dcast(dt_timeseries, global_id ~ t)
  global_id <- dt_timeseries$global_id
  dt_timeseries <- dt_timeseries[, 2:ncol(dt_timeseries)]
  
  dt_timeseries <- as.data.frame(t(dt_timeseries))
  dt_timeseries$t <- as.numeric(rownames(dt_timeseries)) / 3600
  rownames(dt_timeseries) <- NULL
  colnames(dt_timeseries) <- c(global_id, "ZT")
  dt_timeseries <- dt_timeseries[, c("ZT", global_id)]                          
  dt_timeseries_t <- t(dt_timeseries)
  global_ids <- colnames(dt_timeseries)[2:ncol(dt_timeseries)]
  colnames(dt_timeseries_t) <- paste0("ZT", dt_timeseries_t[1, ])
  dt_timeseries_t<-dt_timeseries_t[2:nrow(dt_timeseries_t), ]
  dt_timeseries_t <- cbind(global_id=global_ids, dt_timeseries_t)
  
  # save all .csvs
  stopifnot(ncol(dt_timeseries) == nrow(dt_summ)+1)
  data.table::fwrite(x = dt_timeseries, file = file.path(folder, paste0(prefix, "_", variable, "_dt_timeseries.csv")), na = "NA")
  # this transposed version is more suitable to copy paste in the google sheet where every timepoint is one column and every fly is one row
  data.table::fwrite(x = dt_timeseries_t, file = file.path(folder, paste0(prefix, "_", variable, "_transposed_dt_timeseries.csv")), na = "NA")
  data.table::fwrite(x = dt_summ, file = file.path(folder, paste0(prefix, "_", variable, "_dt_summ.csv")), na = "NA")
  
  # save trace
  suppressWarnings(ggsave(filename = file.path(folder, paste0(prefix, "_", variable, "_trace.png")), plot = gg, height=20, width=20))
  return(NULL)
}

#' @import data.table
load_ethoscop2idoc_map <- function(folder) {
  paths <- list.files(folder)   
  
  mapping_file <- paths[paths == "ID_reassignments.csv"]
  if (length(mapping_file) == 1) {
    ethoscope2idoc_map <- data.table::fread(mapping_file)
    ethoscope2idoc_map <- ethoscope2idoc_map[post !="Excluded",]
  } else if (length(mapping_file) > 1) {
    stop("More than 1 mapping file found")
  } else {
    ethoscope2idoc_map <- data.table(pre=1:20, post=1:20, etho=1:20)
  }
  # the IDOC roi of the animal is given by its pre roi (regardless of what the post was)
  ethoscope2idoc_vector_map <- ethoscope2idoc_map$pre
  names(ethoscope2idoc_vector_map) <- paste0("ROI_", as.character(ethoscope2idoc_map$etho))
  return(ethoscope2idoc_vector_map)
  
}

#' Document IDOC LTM experiment with ethoscope data
#' 
#' Your IDOC folder must contain
#' 1) A valid metadata.cv file with metadata in the filename
#' 2) An ID_reassignments.csv file with columns pre,post,etho
#' @import data.table
#' @import behavr
#' @import scopr
#' @import sleepr
#' @importFrom stringr str_pad
#' @export
process_folder <- function(folder) {    
  
  prefix <- gsub(pattern = "IDOC_sleep_monitoring_", x = basename(folder), replacement = "")
  
  # load metadata
  paths <- list.files(folder)   
  metadata_file <-paths[grep(pattern = "metadata", x=paths)]
  metadata <- data.table::fread(file.path(folder, metadata_file))
  
  
  # load mapping assigment
  ethoscope2idoc_vector_map <- load_ethoscop2idoc_map(folder)
  
  # link metadata
  metadata <- scopr::link_ethoscope_metadata(metadata, result_dir = "/ethoscope_data/results")
  
  # build global id (works across ethoscope and idoc)
  ethoscope_number <- stringr::str_pad(string = as.integer(gsub(pattern = "ETHOSCOPE_", replacement = "", x = metadata$machine_name)), width = 2, pad = "0")
  idoc_rois <- stringr::str_pad(ethoscope2idoc_vector_map[paste0("ROI_", metadata$region_id)], width=2, pad="0")
  metadata$global_id <- paste0(prefix, "_e", ethoscope_number, "_", "roi_", stringr::str_pad(metadata$region_id, width = 2, pad = "0"), "-IDOC_roi_", idoc_rois)
  metadata$short_id <- paste0("roi_", stringr::str_pad(metadata$region_id, width = 2, pad = "0"), "-IDOC_roi_", stringr::str_pad(ethoscope2idoc_vector_map[metadata$region_id], width=2, pad="0"))
  
  masking_duration <- metadata$masking_duration
  if (is.null(masking_duration)) {
    masking_duration <- 6
  } else {
    masking_duration <- 0
  }
  
  # load data
  dt_sleep <- scopr::load_ethoscope(
    metadata=metadata, cache="/ethoscope_data/cache", verbose=TRUE, reference_hour=NA,
    FUN=sleepr::sleep_annotation, velocity_correction_coef=0.0048, time_window_length=10, min_time_immobile=300,
    masking_duration=masking_duration
  )
  
  # bin sleep and interactions every 30 minutes
  dt <- behavr::bin_apply_all(dt_sleep, y="asleep", x_bin_length=behavr::mins(30), FUN=mean)
  dt_interactions <- behavr::bin_apply_all(dt_sleep, y="interactions", x_bin_length=behavr::mins(30), FUN=mean)
  
  # save results
  make_outputs(dt, "asleep", folder, prefix)
  make_outputs(dt_interactions, "interactions", folder, prefix)
}
