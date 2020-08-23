context("idocr")

testthat::test_that("idocr works", {
  
  experiment_folder <- system.file("example", package = "idocr")
  res <- idocr(experiment_folder = experiment_folder)
  res$gg
  
  experiment_folder <- system.file("2020-08-17_19-32-03", package = "idocr")
  res <- idocr(experiment_folder = experiment_folder)
  res$gg
  
})

testthat::test_that("selection of CS+ works", {
  experiment_folder <- system.file("example", package = "idocr")
  res <- idocr(experiment_folder = experiment_folder)
  res$gg
  res$pi
  
  res2 <- idocr(experiment_folder = experiment_folder, CSplus = "TREATMENT_B")
  res2$pi
  
  expect_equal(res$pi$preference_index, res2$pi$preference_index * -1) 
  
  
})