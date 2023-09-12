testthat::test_that("idocr works", {

  pkg_name <- testing_package()

  experiment_folder <- system.file(
    "extdata/real", package = pkg_name,
    mustWork = TRUE
  )

  result <- idocr(experiment_folder = experiment_folder, CSplus_idx = 1,
               min_exits_required = 5, border_mm = 12.5, delay = 0)
  # if we get here without errors, we can tell it minimally works!
  # vdiffr::expect_doppelganger("bb-idocr_main", result[[1]]$gg)
  # expect_snapshot_value(
  #   result[[1]]$pi,
  #   style = "serialize", cran = FALSE
  # )
  
  pref_ids <- na.omit(result[[1]]$pi$preference_index)
  
  
  expect_true(all(attr(pref_ids, "na.action") == c(2, 3, 4, 8, 9, 10, 11, 12)))
  expect_true(all(
    round(pref_ids, digits = 2) == c(
      0.2, -0.14, 0.71, 0.2, -0.2
      )
    )
  )
  
})

# test_that("passing a new label updates the legend", {
# 
#   pkg_name <- testing_package()
# 
#   experiment_folder <- system.file(
#     "extdata/toy", package = pkg_name,
#     mustWork = TRUE
#   )
# 
#   result <- idocr(experiment_folder = experiment_folder, CSplus_idx = 1,
#                   min_exits_required = 5, border_mm = 12.5, delay = 0, labels = LETTERS[1:2],
#                   subtitle = "Updated labels to A and B")
# 
#   vdiffr::expect_doppelganger("bb-idocr_custom-labels", result[[1]]$gg)
# })
# 
# test_that("passing a different minimum of exits updates the results", {
# 
#   pkg_name <- testing_package()
# 
#   experiment_folder <- system.file(
#     "extdata/toy", package = pkg_name,
#     mustWork = TRUE
#   )
# 
#   result <- idocr(experiment_folder = experiment_folder, CSplus_idx = 1,
#                   min_exits_required = 2, # very lenient
#                   border_mm = 12.5, delay = 0,
#                   subtitle = "min_exits_required=2")
# 
#   vdiffr::expect_doppelganger("bb-idocr_custom-min-exits", result[[1]]$gg)
#   expect_snapshot_value(
#     result[[1]]$pi,
#     style = "serialize", cran = FALSE
#   )
# })
# 
# 
# test_that("passing a different decision zone border updates the results", {
# 
#   pkg_name <- testing_package()
# 
#   experiment_folder <- system.file(
#     "extdata/toy", package = pkg_name,
#     mustWork = TRUE
#   )
# 
#   result <- idocr(experiment_folder = experiment_folder, CSplus_idx = 1,
#                   min_exits_required = 5,
#                   border_mm = 5, delay = 0,
#                   subtitle = "border of decision zone=5 mm")
# 
#   vdiffr::expect_doppelganger("bb-idocr_custom-border", result[[1]]$gg)
#   expect_snapshot_value(
#     result[[1]]$pi,
#     style = "serialize", cran = FALSE
#   )
# })
# 
# 
# test_that("CSplus_idx can be set to 2", {
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
#                   border_mm = 12.5, delay = 0,
#                   subtitle = "CS+=TREATMENT_B")
# 
#   vdiffr::expect_doppelganger("bb-idocr_CSplusB", result[[1]]$gg)
#   expect_snapshot_value(
#     result[[1]]$pi,
#     style = "serialize", cran = FALSE
#   )
# })
# 
# 
# # TODO This test does not really test if delay can be non 0
# # if tests whether idocr emits any warning (because of delay being non 0)
# # but also maybe for another reason!
# # At least we know if this is the only test that fails,
# # we know it's because of the delay
# test_that("delay can be non 0", {
#   
#   pkg_name <- testing_package()
#   
#   experiment_folder <- system.file(
#     "extdata/toy", package = pkg_name,
#     mustWork = TRUE
#   )
#   
#   status <- tryCatch({
#      result <- idocr(
#       experiment_folder = experiment_folder, CSplus_idx = 2,
#       min_exits_required = 5,
#       border_mm = 12.5, delay = 5,
#       subtitle = "CS+=TREATMENT_B"
#      )
#      0
#      }
#     , warning = function(w) {
#       1
#     })
#   
#   expect_equal(status, 0)
#   
# })


