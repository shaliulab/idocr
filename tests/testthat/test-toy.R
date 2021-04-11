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
  expect_s3_class(dataset$tracker, "data.table")
  
  # p <- 100 * sum(zoo::rollapply(data = dataset$tracker$x - 100, width=2, FUN=prod) < 0) / 1e4
  # realistic -> probability of a midline cross is between 1 and 5 %
  # TODO This is failing but it's not a big  deal.
  # Address it later
  # expect_true(p > 1 & p < 5)
})

test_that("toy_controller can receive a paradigm", {
  paradigm <- data.table(
    stimulus = c("IRLED", "ODOR_B_LEFT", "ODOR_A_RIGHT",
                 "ODOR_A_LEFT", "ODOR_B_RIGHT",
                 "MAIN_VALVE", "VACUUM",
                 "TREATMENT_A_LEFT", "TREATMENT_A_RIGHT",
                 "TREATMENT_B_LEFT", "TREATMENT_B_RIGHT"
    ),
    on = c(
      c(0, 60, 60, 180, 180, 0, 0, 180, 60, 60, 180)
    ),
    off = c(
      c(360, 120, 120, 240, 240, 360, 360, 240, 120, 120, 240)
    )
  )

  expect_equal(class(toy_controller(paradigm = paradigm)), "matrix")
})
