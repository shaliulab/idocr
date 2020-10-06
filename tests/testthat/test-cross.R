context("cross")

testthat::test_that("overlap_cross_events finds expected number of exits and segregation is correct", {
  
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
  
  expect_equal(nrow(apetitive[apetitive$region_id == 1, ]), 3)
  expect_equal(nrow(apetitive[apetitive$region_id == 2, ]), 1)
  
  expect_equal(nrow(apetitive[aversive$region_id == 1, ]), 1)
  expect_equal(nrow(apetitive[aversive$region_id == 2, ]), 3)
  
})


testthat::test_that("seconds_mask masks correctly", {
  
  side <- c(-1, 1, -1, 1, 1, -1, 1, -1, 1, 1)
  side <- c(side, -side)
  t <- 1:10
  t <- 10 * t
  cross_data <- data.frame(region_id = rep(1:2, each = 10),
                           t = rep(t, times = 2),
                           side = side)
  
  expect_equal(nrow(seconds_mask(cross_data, duration = 1)), nrow(cross_data))
  
  side <- c(-1, 1, -1, 1, 1, -1, 1, -1, 1, 1)
  side <- c(side, -side)
  t <- c(1, 13, 25, 28, 35, 37, 60, 70, 80, 90)
  cross_data <- data.frame(region_id = rep(1:2, each = 10),
                           t = rep(t, times = 2),
                           side = side)

  
  
  cross_data <- seconds_mask(cross_data, duration = 5)
  
  expect_equal(nrow(cross_data), 16)
  # expect 28 and 37 to be gone because these exits happened
  # 3 and 2 seconds after the last one, which is less than the max duration allowed
  # 5 in this case
  expect_false(any(c(28, 37) %in% unique(cross_data$t)))
  
})