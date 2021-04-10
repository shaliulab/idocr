library(testthat)
context("load")


experiment_folder <- system.file(
  "extdata/toy", package = "idocr",
  mustWork = TRUE
)

test_that("load_dataset can read all files in the .csv database", {

  dataset <- load_dataset(experiment_folder)
  
  # check it has the right entries
  expect_equal(
    sort(c("tracker", "controller")),
    sort(names(dataset))
  )
  
  expect_equal(nrow(dataset$tracker), 120000)
  
  expect_equal(sum(dataset$controller[, "ODOR_A_RIGHT"]), 119)
  expect_equal(sum(dataset$controller[, "ODOR_B_LEFT"]) , 119)
  expect_equal(sum(dataset$controller[, "ODOR_A_RIGHT"]), 119)
  expect_equal(sum(dataset$controller[, "ODOR_B_LEFT"]) , 119)
})
  
test_that("preprocess_dataset works", {
  
  dataset_raw <- toy_dataset_small()
  dataset <- load_dataset(experiment_folder)
  # dataset_raw <- list(
  #   tracker = dataset_raw$tracker,
  #   controller = dataset_raw$controller
  # )
  
  preprocessed <- preprocess_dataset(
    experiment_folder,
    dataset = dataset,
    )

  # TODO Maybe I can make the default toy dataset more convenient...
  expect_equal(c(-85.5, 54.5), preprocessed$limits)
  expect_equal(11.5, preprocessed$border)
  expect_equal(120000, nrow(preprocessed$tracker))
  expect_equal(721, nrow(preprocessed$controller))
  
  expect_equal(
    sort(c("tracker", "controller",
           "limits", "border",
           "treatments", "stimuli",
           "CSplus", "CSminus"
         )),
    sort(names(preprocessed))
  )
  
  
})