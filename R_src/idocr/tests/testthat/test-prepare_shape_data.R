context("prepare_shape_data")

testthat::test_that("prepare_shape_data", {
  
  controller_data <- toy_controller()
  shape_data <- prepare_shape_data(controller_data, hardware = "TREATMENT_A_LEFT")
  ref_data <- data.table(group = 0, x = c(-1,0,0,-1), t = c(240, 240, 300, 300),
                         side = -1, hardware_ = "TREATMENT_A_LEFT")
  
  
  expect_true(all_equal(ref_data, shape_data))
  
  shape_data <- prepare_shape_data(controller_data, hardware = "TREATMENT_A_RIGHT")
  ref_data <- data.table(group = 0, x = c(0,1,1,0), t = c(60, 60, 120, 120),
                         side = 1, hardware_ = "TREATMENT_A_RIGHT")
  
  expect_true(all_equal(ref_data, shape_data))
})
