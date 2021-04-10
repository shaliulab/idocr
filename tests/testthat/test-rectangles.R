library(testthat)
library(data.table)
context("rectangles")

controller_data <- toy_controller_small()

test_that("rectangles are built ok", {

  rectangle <- define_rectangle(controller_data, stimulus = "TREATMENT_A_LEFT")
  expect_equal(rectangle$x, c(-1, 0, 0, -1))
  expect_equal(rectangle$t, c(1, 1, 3, 3))
  expect_equal(rectangle$stimulus, rep("TREATMENT_A_LEFT", 4))
  expect_equal(rectangle$side, rep(-1, 4))

  rectangle <- define_rectangle(controller_data, stimulus = "TREATMENT_B_RIGHT")
  expect_equal(rectangle$x, c(0, 1, 1, 0))
  expect_equal(rectangle$t, c(1, 1, 3, 3))
  expect_equal(rectangle$stimulus, rep("TREATMENT_B_RIGHT", 4))
  expect_equal(rectangle$side, rep(1, 4))

  rectangle <- define_rectangle(controller_data, stimulus = "TREATMENT_A_RIGHT")
  expect_equal(rectangle$x, c(0, 1, 1, 0))
  expect_equal(rectangle$t, c(3, 3, 5, 5))
  expect_equal(rectangle$stimulus, rep("TREATMENT_A_RIGHT", 4))
  expect_equal(rectangle$side, rep(1, 4))
  
  # remove the recording of the switch off of one of the components
  corruped_data <- controller_data[1:(nrow(controller_data)-1),]
  error <- expect_error(define_rectangle(corruped_data, stimulus = "TREATMENT_A_RIGHT"))
  expect_equal(error$message, "Problem parsing an end timestamp for TREATMENT_A_RIGHT")
})


test_that("rectangles are inferred properly", {
  

  dataset <- list(
    controller = controller_data,
    treatments = c("TREATMENT_A", "TREATMENT_B"),
    stimuli = colnames(controller_data)[1:4],
    limits = c(-100, 100)
  )
  
  rectangle_data <- define_rectangle_all(dataset)
  
  expect_equal(length(rectangle_data), 4)
  expect_equal(rectangle_data[[1]]$x, c(-100, 0, 0, -100))
  expect_equal(rectangle_data[[2]]$x, c(0, 100, 100, 0))
})
