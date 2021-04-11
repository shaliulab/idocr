test_that("preference_index formula is implemented well and yields the expected result", {
  
  expect_equal(preference_index(appetitive = 5, aversive = 5, min_exits_required = 5), 0)
  expect_equal(preference_index(appetitive = 5, aversive = 10, min_exits_required = 5), -1/3)
})

test_that("preference_index returns NA when the minimum amount of exits is not hit", {
  expect_equal(preference_index(appetitive = 4, aversive = 0, min_exits_required = 5), NA)
})

test_that("if all exits are on one side, the index is 1 or -1", {
  expect_equal(preference_index(appetitive = 5, aversive = 0, min_exits_required = 5), 1)
  expect_equal(preference_index(appetitive = 0, aversive = 5, min_exits_required = 5), -1)
})

test_that("compute_preference_index calls preference_index successfully during analysis", {
  
  annotated_data <- toy_annotation_data()
  pref_data <- compute_preference_index(annotated_data)
  expect_equal(pref_data$preference_index, 0.6)
  expect_equal(pref_data$appetitive, 8)
  expect_equal(pref_data$aversive, 2)
})

test_that("compute_preference_index produces NA when the minimum exits required are not met", {
  
  short_data <- toy_annotation_data()[1:4, ] 
  # require 1 more than the number of crosses available
  # no matter what the data is, the result should be NA
  pref_data <- compute_preference_index(short_data, min_exits_required = 5)
  expect_equal(pref_data$preference_index, NA)
  expect_equal(pref_data$appetitive, nrow(short_data[short_data$type == "appetitive",]))
  expect_equal(pref_data$aversive, nrow(short_data[short_data$type == "aversive",]))
})