## code to prepare `DATASET` dataset goes here
# library(idocr)
set.seed(2021)

##### - Generate a toy dataset for testing purposes
dest = file.path("inst", "extdata", "toy")
steps = 6000
paradigm <- data.table(
  stimulus = c("IRLED", "ODOR_B_LEFT", "ODOR_A_RIGHT",
               "ODOR_A_LEFT", "ODOR_B_RIGHT",
               "MAIN_VALVE", "VACUUM",
               "TREATMENT_A_LEFT", "TREATMENT_A_RIGHT",
               "TREATMENT_B_LEFT", "TREATMENT_B_RIGHT"
  ),
  on = c(
    c(0, 60, 60, 180, 180, 0, 0, 180, 60, 60, 180)
  ),
  off = c(
    c(360, 120, 120, 240, 240, 360, 360, 240, 120, 120, 240)
  )
)

toy_dataset <- generate_toy_dataset(dest, steps=steps, paradigm=paradigm)
usethis::use_data(toy_dataset, overwrite = TRUE)
