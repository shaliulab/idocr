library(testthat)
context("load")

test_that("toy dataset is loaded ok", {
  experiment_folder <- system.file(
    "extdata/toy", package = "idocr",
    mustWork = TRUE
  )
  
  dataset <- load_dataset(experiment_folder, delay=0)
  
  # check it has the right entries
  expect_equal(
    sort(c("roi", "controller", "limits")),
    sort(names(dataset))
  )
  
  expect_equal(nrow(dataset$roi), 120000)
  
  expect_equal(sum(dataset$controller[, "ODOR_A_RIGHT"]), 119)
  expect_equal(sum(dataset$controller[, "ODOR_B_LEFT"]) , 119)
  expect_equal(sum(dataset$controller[, "ODOR_A_RIGHT"]), 119)
  expect_equal(sum(dataset$controller[, "ODOR_B_LEFT"]) , 119)
})
  