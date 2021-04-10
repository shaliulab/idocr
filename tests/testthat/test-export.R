context("export")
library(testthat)
library(magrittr)


test_that("pi_summary is exported and animals with less than minimum exists have a NA PI", {

  experiment_folder <- system.file(
    "extdata/toy", package = "idocr",
    mustWork = TRUE
  )
  pi <- toy_pi_data()
  min_exits_required <- 5
  
  na_rows <- (pi$appetitive + pi$aversive) < min_exits_required
  pi[na_rows, "preference_index"] <- NA
  
  pi_path <- export_pi_summary(experiment_folder = experiment_folder, pi = pi)
  raw_data <- readLines(pi_path)[-1]
  
  # all saved pi in the rows where pi is NA is also NA
  expect_equal(
    raw_data[na_rows] %>%
      lapply(., function(x) strsplit(x, split = ",") %>% unlist %>% .[4]) %>%
      unlist %>%
      unique,
    "NA"
  )
  
  # none of the saved pi in the rows where the pi is not NA is NA
  expect_false(
    any(is.na(raw_data[!na_rows] %>%
      lapply(., function(x) strsplit(x, split = ",") %>% unlist %>% .[4]) %>%
      unlist
    ))
  )
})

test_that("main summary matches expectation in the saved file", {
  
  experiment_folder <- system.file(
    "extdata/toy", package = "idocr",
    mustWork = TRUE
  )
  
  tracker_data <- toy_tracker_small()
  controller_data <- toy_controller_small()
  
  summmary_data <- export_summary(
    experiment_folder = experiment_folder,
    output_csv = NULL,
    tracker_data = tracker_data,
    controller_data = controller_data
  )

  local_edition(3)
  expect_snapshot_value(
    summmary_data, 
    style = "serialize", cran = FALSE
  )
})

test_that("export_dataset runs without issues", {
  
  experiment_folder <- system.file(
    "extdata/toy", package = "idocr",
    mustWork = TRUE
  )
  
  tracker_data <- toy_tracker_small()
  controller_data <- toy_controller_small()
  pi_data <- toy_pi_data()
  
  analysis <- list(pi=pi_data[pi_data$region_id %in% unique(tracker_data$region_id), ])
  dataset <- list(
    tracker = tracker_data,
    controller = controller_data
  )
  
  all_exports <- export_dataset(experiment_folder = experiment_folder,
                 dataset = dataset, analysis = analysis)
  
  expect_true(file.exists(
      build_filename(experiment_folder = experiment_folder, key = "SUMMARY")
  ))
  expect_true(file.exists(
    build_filename(experiment_folder = experiment_folder, key = "PI")
  ))
  
  local_edition(3)
  expect_snapshot_value(
    all_exports, 
    style = "serialize", cran = FALSE
  )
  
  
})
