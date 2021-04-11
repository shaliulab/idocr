testthat::test_that("idocr works", {

  experiment_folder <- system.file("extdata/toy", package = "idocr",
                                   mustWork = TRUE
                                   )
  result <- idocr(experiment_folder = experiment_folder, CSplus_idx = 1,
               min_exits_required = 5, border_mm = 12.5, delay = 0)
  # if we get here without errors, we can tell it minimally works!
  vdiffr::expect_doppelganger("gg1", result$gg)
  expect_snapshot_value(
    result$pi, 
    style = "serialize", cran = FALSE
  )
})

test_that("passing a new label updates the legend", {

  experiment_folder <- system.file("extdata/toy", package = "idocr",
                                   mustWork = TRUE
  )
  
  result <- idocr(experiment_folder = experiment_folder, CSplus_idx = 1,
                  min_exits_required = 5, border_mm = 12.5, delay = 0, labels = LETTERS[1:2],
                  subtitle = "Updated labels to A and B")
  
  vdiffr::expect_doppelganger("gg2", result$gg)
})

test_that("passing a different minimum of exits updates the results", {
  
  experiment_folder <- system.file("extdata/toy", package = "idocr",
                                   mustWork = TRUE
  )
  
  result <- idocr(experiment_folder = experiment_folder, CSplus_idx = 1,
                  min_exits_required = 2, # very lenient
                  border_mm = 12.5, delay = 0,
                  subtitle = "min_exits_required=2")
  
  vdiffr::expect_doppelganger("gg3", result$gg)
  expect_snapshot_value(
    result$pi, 
    style = "serialize", cran = FALSE
  )
})


test_that("passing a different decision zone border updates the results", {
  
  experiment_folder <- system.file("extdata/toy", package = "idocr",
                                   mustWork = TRUE
  )
  
  result <- idocr(experiment_folder = experiment_folder, CSplus_idx = 1,
                  min_exits_required = 5,
                  border_mm = 5, delay = 0,
                  subtitle = "border of decision zone=5 mm")

  vdiffr::expect_doppelganger("gg4", result$gg)
  expect_snapshot_value(
    result$pi, 
    style = "serialize", cran = FALSE
  )
})


test_that("CSplus_idx can be set to 2", {
  
  experiment_folder <- system.file("extdata/toy", package = "idocr",
                                   mustWork = TRUE
  )
  
  result <- idocr(experiment_folder = experiment_folder, CSplus_idx = 2,
                  min_exits_required = 5,
                  border_mm = 12.5, delay = 0,
                  subtitle = "CS+=TREATMENT_B")
  
  vdiffr::expect_doppelganger("gg5", result$gg)
  expect_snapshot_value(
    result$pi, 
    style = "serialize", cran = FALSE
  )
})
