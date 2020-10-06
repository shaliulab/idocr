context("cross")

testthat::test_that("overlap_cross_events works", {
  
  side <- c(-1, 1, -1, 1, 1, -1, 1, -1, 1, 1)
  side <- c(side, -side)
  t <- 1:10
  t <- 10 * t
    cross_data <- data.frame(region_id = rep(1:2, each = 10),
                           t = rep(t, times = 2),
                           side = side)
  event_data <- data.frame(
    hardware_ = c("CSplus", "CSminus"),
    t_start = c(30,30) * 1000,
    t_end = c(80, 80) * 1000,
    side = c(1, -1),
    hardware_small = c("CSplus", "CSminus")
  )
  
  
  apetitive <- overlap_cross_events(
        cross_data = cross_data,
        event_data = event_data[event_data$hardware_small == "CSplus",],
        type = "apetitive", mask_FUN = seconds_mask
  )
  
  aversive <- overlap_cross_events(
    cross_data = cross_data,
    event_data = event_data[event_data$hardware_small == "CSminus",],
    type = "aversive", mask_FUN = seconds_mask
  )
  
  
})