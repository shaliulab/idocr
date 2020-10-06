context("idocr")

testthat::test_that("idocr works", {
  
  experiment_folder <- system.file("2020-10-05_13-05-51", package = "idocr")
  res <- idocr(experiment_folder = experiment_folder, treatments = c("OCT", "MCH"))
  # if we get here without errors, we can tell it minimally works!
  res$gg
  
})

testthat::test_that("selection of CS+ works", {
  experiment_folder <- system.file("example", package = "idocr")
  res <- idocr(experiment_folder = experiment_folder,
               treatments = c("OCT", "MCH"))
  
  res2 <- idocr(experiment_folder = experiment_folder,
                CSplus = "TREATMENT_B",
                treatments = c("OCT", "MCH"))
  res2$pi
  
  expect_equal(res$pi$preference_index, res2$pi$preference_index * -1) 
  
  
})