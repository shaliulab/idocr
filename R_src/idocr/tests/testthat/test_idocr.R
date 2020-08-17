context("idocr")

testthat::test_that("idocr works", {
  
  experiment_folder <- system.file("example", package = "idocr")
  res <- idocr(experiment_folder = experiment_folder)
  res$gg
  
})