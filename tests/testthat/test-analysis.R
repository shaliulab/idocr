library(testthat)
context("analysis")

test_that("rectangles are inferred properly", {

  
  experiment_folder <- system.file(
    "extdata/toy", package = "idocr",
    mustWork = TRUE
  )
  
  dataset <- preprocess_dataset(experiment_folder, idocr::toy_dataset)
  
})