context("BehaviorAnalyzer")

exp_folder <- "lemdt_results/2019-11-22_12-46-26"
decision_zone_mm <- 10
min_exits_required <- 5
max_time_minutes <- 60
A <- NULL
B <- NULL
selected_flies <- 1:20
annotation <- ""
debug <- F
index_function <- LeMDTr::preference_index

lemdt_analysis <- LeMDTr::BehaviorAnalyzer$new(experiment_folder = exp_folder, decision_zone_mm = decision_zone_mm, min_exits_required = min_exits_required, max_time_minutes = max_time_minutes)
first_colnames <- c("frame", "arena", "cx", "cy", "datetime", "t", "ODOUR_A_LEFT", "ODOUR_A_RIGHT", "ODOUR_B_LEFT", "ODOUR_B_RIGHT", "eshock_left", "eshock_right", "mm")

testthat::test_that("read_experiment works", {

  # lemdt_result should initialize as null
  expect_null(lemdt_analysis$lemdt_result)
  lemdt_analysis$read_experiment()
  # checkt lemdt_result is now a populated data.table
  expect_is(lemdt_analysis$lemdt_result, c("data.frame", "data.table"))
  expect_true(nrow(lemdt_analysis$lemdt_result) > 0)
  
  # check odours and paradigm too
  expect_identical(self$odours, c("OCT", "MCH"))
  expect_true(nrow(self$paradigm) > 0)

  
  lemdt_analysis$px2mm()
  lemdt_result <- lemdt_analysis$lemdt_result
  expect_true(all(first_colnames %in% colnames(lemdt_result)) & all(colnames(lemdt_result) %in% first_colnames))

  
})

testthat::test_that("add_period_column works", {
  
  lemdt_analysis$add_period_column()  
  lemdt_analysis$lemdt_result$period
  
  
})
# test that the periods are contiguous!!
# test taht prepare_rect_data fill variable is not na