testthat::test_that("idocr works", {

  pkg_name <- testing_package()
  
  experiment_folder <- system.file(
    "extdata/toy", package = pkg_name,
    mustWork = TRUE
  )
  
  result <- idocr(experiment_folder = experiment_folder, CSplus_idx = 1,
               min_exits_required = 5, border_mm = 12.5, delay = 0)
  # if we get here without errors, we can tell it minimally works!
  vdiffr::expect_doppelganger("idocr_main", result[[1]]$gg)
  expect_snapshot_value(
    result[[1]]$pi, 
    style = "serialize", cran = FALSE
  )
})

test_that("passing a new label updates the legend", {

  pkg_name <- testing_package()
  
  experiment_folder <- system.file(
    "extdata/toy", package = pkg_name,
    mustWork = TRUE
  )
  
  result <- idocr(experiment_folder = experiment_folder, CSplus_idx = 1,
                  min_exits_required = 5, border_mm = 12.5, delay = 0, labels = LETTERS[1:2],
                  subtitle = "Updated labels to A and B")
  
  vdiffr::expect_doppelganger("idocr_custom-labels", result[[1]]$gg)
})

test_that("passing a different minimum of exits updates the results", {
  
  pkg_name <- testing_package()
  
  experiment_folder <- system.file(
    "extdata/toy", package = pkg_name,
    mustWork = TRUE
  )
  
  result <- idocr(experiment_folder = experiment_folder, CSplus_idx = 1,
                  min_exits_required = 2, # very lenient
                  border_mm = 12.5, delay = 0,
                  subtitle = "min_exits_required=2")
  
  vdiffr::expect_doppelganger("idocr_custom-min-exits", result[[1]]$gg)
  expect_snapshot_value(
    result[[1]]$pi, 
    style = "serialize", cran = FALSE
  )
})


test_that("passing a different decision zone border updates the results", {
  
  pkg_name <- testing_package()
  
  experiment_folder <- system.file(
    "extdata/toy", package = pkg_name,
    mustWork = TRUE
  )
  
  result <- idocr(experiment_folder = experiment_folder, CSplus_idx = 1,
                  min_exits_required = 5,
                  border_mm = 5, delay = 0,
                  subtitle = "border of decision zone=5 mm")

  vdiffr::expect_doppelganger("idocr_custom-border", result[[1]]$gg)
  expect_snapshot_value(
    result[[1]]$pi, 
    style = "serialize", cran = FALSE
  )
})


test_that("CSplus_idx can be set to 2", {
  
  pkg_name <- testing_package()
  
  experiment_folder <- system.file(
    "extdata/toy", package = pkg_name,
    mustWork = TRUE
  )
  
  result <- idocr(experiment_folder = experiment_folder, CSplus_idx = 2,
                  min_exits_required = 5,
                  border_mm = 12.5, delay = 0,
                  subtitle = "CS+=TREATMENT_B")
  
  vdiffr::expect_doppelganger("idocr_CSplusB", result[[1]]$gg)
  expect_snapshot_value(
    result[[1]]$pi, 
    style = "serialize", cran = FALSE
  )
})



test_that("analysis mask works", {
  
  pkg_name <- testing_package()
  
  experiment_folder <- system.file(
    "extdata/toy", package = pkg_name,
    mustWork = TRUE
  )
  
  result <- idocr(experiment_folder = experiment_folder, CSplus_idx = 2,
                  min_exits_required = 5,
                  analysis_mask = list(FIRST_TWO_MINS = c(0, 120)),
                  border_mm = 12.5, delay = 0,
                  subtitle = "analysis_mask=[0,120]")
  
  vdiffr::expect_doppelganger("idocr_analysis-mask", result[[1]]$gg)
  expect_snapshot_value(
    result[[1]]$pi, 
    style = "serialize", cran = FALSE
  )
})

test_that("analysis mask takes more than 1 mask", {

  pkg_name <- testing_package()
  
  experiment_folder <- system.file(
    "extdata/toy", package = pkg_name,
    mustWork = TRUE
  )
  
  
  result <- idocr(experiment_folder = experiment_folder, CSplus_idx = 2,
                  min_exits_required = 5,
                  analysis_mask = list(
                    FIRST_TWO_MINS = c(0, 120),
                    SECOND_BLOCK = c(120, 240)
                  ),
                  border_mm = 12.5, delay = 0,
                  subtitle = "")
  
  vdiffr::expect_doppelganger("idocr_analysis-multimask1", result[[1]]$gg + labs(
    "analysis_mask=[0,120]"
  ))
  vdiffr::expect_doppelganger("idocr_analysis-multimask2", result[[2]]$gg + labs(
    "analysis_mask=[120,240]"
  ))
  
  expect_snapshot_value(
    result[[1]]$pi, 
    style = "serialize", cran = FALSE
  )
  expect_snapshot_value(
    result[[2]]$pi, 
    style = "serialize", cran = FALSE
  ) 
  
})

test_that("plot mask works", {
  
  pkg_name <- testing_package()
  
  experiment_folder <- system.file(
    "extdata/toy", package = pkg_name,
    mustWork = TRUE
  )
  
  result <- idocr(experiment_folder = experiment_folder, CSplus_idx = 2,
                  min_exits_required = 5,
                  plot_mask = c(0, 180),
                  border_mm = 12.5, delay = 0,
                  subtitle = "plot_mask=[0,180]")
  
  vdiffr::expect_doppelganger("idocr_plot-mask", result[[1]]$gg)
})