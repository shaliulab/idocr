test_that("analysis mask works", {

  pkg_name <- testing_package()

  experiment_folder <- system.file(
    "extdata/real2", package = pkg_name,
    mustWork = TRUE
  )

  result <- idocr(experiment_folder = experiment_folder, CSplus_idx = 2,
                  min_exits_required = 5,
                  analysis_mask = list(FIRST_TWO_MINS = c(0, 120)),
                  border_mm = 12.5, delay = 0,
                  subtitle = "analysis_mask=[0,120]")

  # vdiffr::expect_doppelganger("dd-idocr-masks_analysis-mask", result[[1]]$gg)
  # expect_snapshot_value(
  #   result[[1]]$pi,
  #   style = "serialize", cran = FALSE
  # )


  result_folder <- file.path(experiment_folder, "FIRST_TWO_MINS")
  # check the subfolder is created
  expect_true(dir.exists(result_folder))
  # check the subfolder is populated
  expect_true(length(list.files(result_folder)) != 0)
  pref_ids <- na.omit(round(result$FIRST_TWO_MINS$pi$preference_index, digits = 3))
  
  expect_true(all(attr(pref_ids, "na.action") == c(7, 20)))
  expect_true(all(pref_ids == c(-0.778, -0.4, -0.714, 0.000, -0.5, 0.2, -0.2,
                                 -1, -0.091, -0.273, -0.4, -0.556, -0.111, -0.111, -0.2, 0, -0.143, 0
                                 )))
  



  # cleanup
  unlink(recursive = T, x = result_folder)

})
# 
# test_that("analysis mask takes more than 1 mask", {
# 
#   pkg_name <- testing_package()
# 
#   experiment_folder <- system.file(
#     "extdata/toy", package = pkg_name,
#     mustWork = TRUE
#   )
# 
# 
#   result <- idocr(experiment_folder = experiment_folder, CSplus_idx = 2,
#                   min_exits_required = 5,
#                   analysis_mask = list(
#                     FIRST_TWO_MINS = c(60, 120),
#                     SECOND_BLOCK = c(180, 240)
#                   ),
#                   border_mm = 12.5, delay = 0,
#                   subtitle = "")
# 
#   vdiffr::expect_doppelganger("dd-idocr-masks_analysis-multimask1", result[[1]]$gg + labs(
#     subtitle = "analysis_mask=[60,120]"
#   ))
#   vdiffr::expect_doppelganger("dd-idocr-masks_analysis-multimask2", result[[2]]$gg + labs(
#     subtitle = "analysis_mask=[180,240]"
#   ))
# 
#   expect_true(result[[1]]$pi[1,]$preference_index == 1)
#   expect_true(is.na(result[[2]]$pi[1,]$preference_index))
# 
#   expect_true(round(result[[1]]$pi[result[[1]]$pi$region_id == 4,]$preference_index, digits = 3) == -0.429)
#   expect_true(result[[2]]$pi[result[[2]]$pi$region_id == 4,]$preference_index == -1)
# })
# 
# test_that("plot mask works", {
# 
#   pkg_name <- testing_package()
# 
#   experiment_folder <- system.file(
#     "extdata/toy", package = pkg_name,
#     mustWork = TRUE
#   )
# 
#   result <- idocr(experiment_folder = experiment_folder, CSplus_idx = 2,
#                   min_exits_required = 5,
#                   plot_mask = c(0, 180),
#                   border_mm = 12.5, delay = 0,
#                   subtitle = "plot_mask=[0,180]")
# 
#   vdiffr::expect_doppelganger("dd-idocr-masks_plot-mask", result[[1]]$gg)
# })
