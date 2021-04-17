test_that("find_exits works", {

  border <- 2
  tracker_data <- toy_tracker_small()
  
  cross_data_left <- find_exits(tracker_data, border, side=-1)
  cross_data_right <- find_exits(tracker_data, border, side=1)
  
  expect_true("region_id" %in% colnames(cross_data_left))
  expect_equal(nrow(cross_data_left[cross_data_left$region_id == 1,]), 2)
  expect_equal(nrow(cross_data_right[cross_data_right$region_id == 1,]), 3)
  expect_equal(nrow(cross_data_left[cross_data_left$region_id == 2,]), 0)
  expect_equal(nrow(cross_data_right[cross_data_right$region_id == 2,]), 0)
})


test_that("find_exits_all works too", {

  border <- 2
  tracker_data <- toy_tracker_small()
  cross_data_left <- find_exits(tracker_data, border, side=-1)
  cross_data_right <- find_exits(tracker_data, border, side=1)

  expect_true(identical(
    find_exits_all(tracker_data, border),
    rbind(cross_data_left, cross_data_right)
  ))
})


test_that("the second mask works", {
  
  # to avoid a warning emitted by seconds_mask when a dt column is
  # already present the cross data cannot contain a dt column
  cross_data_left <- tibble::tibble(id="toy|01", region_id=1, t=c(1, 9))
  
  cross_data_left_masked <- seconds_mask(cross_data = cross_data_left, min_time = 0) %>%
    dplyr::select(-dt)
  # expect both should be identical, since the mask is of length 0
  # ignore the dt column
  expect_identical(
    cross_data_left,
    cross_data_left_masked
    )
  
  cross_data_left_masked <- seconds_mask(cross_data = cross_data_left, min_time = 10)  %>%
    dplyr::select(-dt)
  # expect only the first cross remains
  # since the second one happens during the masking period (within 10 seconds)
  expect_identical(
    cross_data_left[1, ],
    cross_data_left_masked
  )
})


test_that("that only crosses happening during the event are counted", {
  
  treatment_1 <- "TREATMENT_A"  
  event_data <- toy_event_data()
  cross_data  <- toy_cross_data()
  
  annotation <- annotate_cross(
    cross_data = cross_data,
    event_data = event_data,
    treatment = treatment_1,
    type = "dummy"
  )
  
  expect_equal(annotation$t, 2)
})

test_that("if the event is extended in time, the second cross is also considered", {

  treatment_1 <- "TREATMENT_A"
  event_data <- toy_event_data()
  cross_data <- toy_cross_data()

  event_data$t_end <- 10000
  
  annotation <- annotate_cross(
    cross_data = cross_data,
    event_data = event_data,
    treatment = treatment_1,
    type = "dummy"
  )
  expect_equal(annotation$t, c(2, 5))  
})

test_that("if the side of the event changes, other exits are considered", {

  treatment_1 <- "TREATMENT_A"
  event_data <- toy_event_data()
  cross_data <- toy_cross_data()
  
  
  event_data$t_end <- 10000
  event_data$side <- -1
  
  annotation <- annotate_cross(
    cross_data = cross_data,
    event_data = event_data,
    treatment = treatment_1,
    type = "dummy"
  )
  expect_equal(annotation$t, c(6, 7, 8))
  
})

test_that("if there is no treatment in the event data that matches the query, the result is null", {
  
  treatment_1 <- "TREATMENT_A"
  treatment_2 <- "TREATMENT_B"
  
  event_data <- toy_event_data()
  cross_data <- toy_cross_data()
  
  event_data$treatment <- treatment_1

  expect_warning({
    annotation <- annotate_cross(
      cross_data = cross_data,
      event_data = event_data,
      treatment = treatment_2,
      type = "dummy"
    )},
    "")
  
  expect_equal(nrow(annotation), 0)  
})


test_that("the treatment name is recorded properly in the annotation", {

  treatment_1 <- "TREATMENT_A"  
  event_data <- toy_event_data()
  cross_data <- toy_cross_data()
  
  annotation <- annotate_cross(
    cross_data = cross_data,
    event_data = event_data,
    treatment = treatment_1,
    type = "dummy"
  )
  expect_true(all(annotation$type == "dummy"))  
})