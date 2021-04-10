# library(testthat)
# context("idocr")
# 
# testthat::test_that("idocr works", {
#   
#   experiment_folder <- system.file("extdata/toy", package = "idocr",
#                                    mustWork = TRUE
#                                    )
#   res <- idocr(experiment_folder = experiment_folder, treatments = c("OCT", "MCH"))
#   # if we get here without errors, we can tell it minimally works!
#   res$gg
#   
# })