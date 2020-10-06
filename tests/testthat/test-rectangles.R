context("rectangles")

testthat::test_that("define_rectangle works", {
  
  controller_data <- toy_controller("2020-10-05_13-05-51")
  rectangle_data <-  define_rectangle(controller_data, hardware = "TREATMENT_A_LEFT")
  expect_equal(nrow(rectangle_data), 4)
  expect_equal(rectangle_data$side, rep(-1, 4))
  expect_equal(rectangle_data$hardware_, rep("TREATMENT_A_LEFT", 4))
  
  rectangle_data <-  define_rectangle(controller_data, hardware = "TREATMENT_B_RIGHT")
  expect_equal(nrow(rectangle_data), 4)
  expect_equal(rectangle_data$side, rep(1, 4))
  expect_equal(rectangle_data$hardware_, rep("TREATMENT_B_RIGHT", 4))
  
  rectangle_data <-  define_rectangle(controller_data, hardware = "TREATMENT_B_LEFT")
  expect_equal(nrow(rectangle_data), 0)
  expect_equal(colnames(rectangle_data), c("group", "x", "t", "side", "hardware_"))

})


testthat::test_that("define_rectangles works", {
  controller_data <- toy_controller("2020-10-05_13-05-51")
  rectangle_data <-  define_rectangles(controller_data,
                                       hardware = c("TREATMENT_A_LEFT", "TREATMENT_B_RIGHT", "TREATMENT_B_LEFT"),
                                       limits = c(-10, 10))
  expect_equal(length(rectangle_data), 2)
  expect_equal(rectangle_data[[1]]$x, c(-10, 0, 0, -10))
  expect_equal(rectangle_data[[2]]$x, c(0, 10, 10, 0))
})
