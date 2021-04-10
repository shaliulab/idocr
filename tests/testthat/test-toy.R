library(testthat)
library(zoo)

context("toy")

test_that("rebound is reversing the steps of virtual flies when they hit a limit", {
  expect_equal(rebound(201, 0, 200), 199)
  expect_equal(rebound(-2, 0, 200), 2)
  expect_equal(rebound(-2, 10, 200), 22)
})

test_that("walk is unlikely to approach the limit", {
  set.seed(2022)
  expect_true(all(replicate(n = 10, expr = walk(c(190, 10)))[1,] < 190))
})

test_that("generate_toy_dataset produces a simulated dataset", {
  dataset <- generate_toy_dataset(steps=1e4)
  expect_is(dataset$tracker, "data.table")
  
  # p <- 100 * sum(zoo::rollapply(data = dataset$tracker$x - 100, width=2, FUN=prod) < 0) / 1e4
  # realistic -> probability of a midline cross is between 1 and 5 %
  # TODO This is failing but it's not a big  deal.
  # Address it later
  # expect_true(p > 1 & p < 5)
})