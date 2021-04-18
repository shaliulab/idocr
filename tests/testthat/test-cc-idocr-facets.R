test_that("Number of rows and columns of layout can be tuned", {

  pkg_name <- testing_package()

  experiment_folder <- system.file(
    "extdata/toy", package = pkg_name,
    mustWork = TRUE
  )

  result <- idocr(experiment_folder = experiment_folder, CSplus_idx = 2,
                  min_exits_required = 5,
                  border_mm = 12.5, delay = 0,
                  subtitle = "All 20 animals should be on one row", nrow=1, ncol=20)

  vdiffr::expect_doppelganger("cc-idocr-facets_one-row", result[[1]]$gg)
})


test_that("Number of rows and columns of layout must match number of animals", {

  pkg_name <- testing_package()

  experiment_folder <- system.file(
    "extdata/toy", package = pkg_name,
    mustWork = TRUE
  )

  expect_error({
    idocr(experiment_folder = experiment_folder, CSplus_idx = 2,
          min_exits_required = 5,
          border_mm = 12.5, delay = 0,
          subtitle = "All 20 animals should be on one row", nrow=1, ncol=10)
  }, regexp = "The passed layout does not match the number of animals.*")
})
