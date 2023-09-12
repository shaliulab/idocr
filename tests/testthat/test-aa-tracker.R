test_that("find_rois lists ROI .csv database correctly", {

  pkg_name <- testing_package()
  
  experiment_folder <- system.file(
    "extdata/toy", package = pkg_name,
    mustWork = TRUE
  )
  
  
  roi_database <- find_rois(experiment_folder)
  roi_filenames <- roi_database %>% lapply(., basename) %>% unlist
  
  expectation <- paste0("2021-01-01_01-01-01_", paste(rep("0", 32), collapse=""), "_ROI_", 1:20, ".csv")
  
  expect_true(all(roi_filenames == expectation))
})

test_that("construct_animal_id works", {
  
  pkg_name <- testing_package()
  
  experiment_folder <- system.file(
    "extdata/toy", package = pkg_name,
    mustWork = TRUE
  )
  
  animal_ids <- construct_animal_id(experiment_folder, 1:20)
  expectation <- paste0("2021-01-01_01-01-01_00000|", stringr::str_pad(1:20, 2, pad="0"))
  expect_true(all(animal_ids == expectation))
})

test_that("remove_duplicates actually removes duplicates", {
  
  tracker_data <- toy_tracker_small()
  tracker_data <- rbind(tracker_data, tracker_data)
  expect_equal(nrow(remove_duplicates(tracker_data)), nrow(toy_tracker_small()))
})

test_that("center around median produces data whose center is at 0", {

  pkg_name <- testing_package()
  
  experiment_folder <- system.file(
    "extdata/toy", package = pkg_name,
    mustWork = TRUE
  )
  
  
  # the x position is always positive in the raw data
  expect_true(min(toy_dataset$tracker$x) > 0)
  expect_true(median(toy_dataset$tracker$x) != 0)
  
  centered <- center_dataset(experiment_folder, toy_dataset$tracker)
  centered_x <- centered %>% group_by(region_id) %>% do(., .[1,]) %>% ungroup %>% .$x %>%
    round(., digits = 1)
  
  expect_true(all(
    centered_x ==
      rep(9,20)
  ))
  
  
})
