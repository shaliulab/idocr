context("preference_index")

testthat::test_that("preference_index works as expected", {
  
  roi_data <- toy_raw()
  crosses <- toy_crosses()
  preference <- crosses$preference
  aversive <- crosses$aversive
  overlap_data <- rbind(
    cbind(
      preference,
      type = "preference"
    ),
    cbind(
      aversive,
      type = "aversive"
    )
  )
  
  min_exits_required <- 5
  
  pi_data <- overlap_data %>%
    dplyr::nest_by(region_id) %>%
    dplyr::summarise(preference_index = preference_index(data, min_exits_required = min_exits_required))
  
  expect_equal(round(pi_data[pi_data$region_id == 1, "preference_index", drop = TRUE], digits = 2), 0.14)
  expect_equal(round(pi_data[pi_data$region_id == 20, "preference_index", drop = TRUE], digits = 2), 0.07)
  
})