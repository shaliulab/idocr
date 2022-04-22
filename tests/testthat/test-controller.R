test_that("get_event_data processes a loaded dataset into a long format table where every combination of stimuli and timepoint have a dedicated row", {

  dataset <- toy_dataset_small()

  event_data <- get_event_data(dataset)
  
  expect_equal(nrow(event_data), 4)
  expect_equal(event_data$t_start, c(1000, 3000, 3000, 1000))
  expect_equal(event_data$t_end, c(3000, 5000, 5000, 3000))
  expect_equal(event_data$stimulus, c(
    "TREATMENT_A_LEFT", "TREATMENT_A_RIGHT",
    "TREATMENT_B_LEFT", "TREATMENT_B_RIGHT"
  ))
  expect_equal(event_data$treatment, c(
    "TREATMENT_A", "TREATMENT_A",
    "TREATMENT_B", "TREATMENT_B"
  ))
})