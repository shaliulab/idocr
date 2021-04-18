test_that("reading a corrupted fields throws a human friendly error", {
  
  pkg_name <- testing_package()
  
  experiment_folder <- system.file(
    "extdata/corrp", package = pkg_name,
    mustWork = TRUE
  )
  
  expect_error(load_controller(experiment_folder), "Corrupted file -> .* Following rows have a number of fields different from the rest \\(24\\).*")
})