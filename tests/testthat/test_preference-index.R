context("preference_index")

testthat::test_that("preference_index works", {
  
  expect_equal(preference_index(apetitive = 5, aversive = 5, min_exits_required = 5), 0)
  expect_equal(preference_index(apetitive = 5, aversive = 10, min_exits_required = 5), -1/3)
  expect_equal(preference_index(apetitive = 4, aversive = 0, min_exits_required = 5), 0)
  expect_equal(preference_index(apetitive = 5, aversive = 0, min_exits_required = 5), 1)
  
})