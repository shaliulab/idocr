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

test_that("main summary ", {
  
  experiment_folder <- system.file(
    "extdata/toy", package = "idocr",
    mustWork = TRUE
  )
  
  tracking_data <- toy_tracker_small()
  controller_data <- toy_controller_small()
  
  summmary_data <- export_summary(
    experiment_folder = experiment_folder,
    output_csv = NULL,
    tracking_data, controller_data
  )

  local_edition(3)
  expect_snapshot_value(
    summmary_data, 
    style = "serialize", cran = FALSE
  )
})
