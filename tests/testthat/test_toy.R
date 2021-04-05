context("toy")

test_that("rebound works as expected", {
  expect_equal(rebound(201, 0, 200), 199)
  expect_equal(rebound(-2, 0, 200), 2)
  expect_equal(rebound(-2, 10, 200), 22)
})

test_that("walk works as expected", {
  set.seed(2022)
  all(replicate(n = 10, expr = walk(c(190, 10)))[1,] < 190)
})

test_that("dataset is realistic", {
  dataset <- generate_toy_dataset(steps=1e4)
  p <- 100 * sum(zoo::rollapply(data = dataset$roi_data$x - 100, width=2, FUN=prod) < 0) / 1e4
  # realistic -> probability of a midline cross is between 1 and 5 %
  expect_true(p > 1 & p < 5)
})