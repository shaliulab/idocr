test_that("idocr is backwards compatible", {
  
  pkg_name <- testing_package()
  
  experiment_folder <- system.file(
    "extdata/real",
    package = pkg_name, mustWork = TRUE
  ) 
  # Change what treatment A and B are
  # to fit it to your needs
  treatment_A <- "OCT"
  treatment_B <- "MCH+ES"
  
  # leave this empty or fill something relevant for the experiment
  # it will appear in the subtitle of the plot
  # (below the big title)
  description <- "Enter a description here"
  
  # Minimal number of exits required to consider the data
  # of one animal significant and then compute a index from it
  min_exits_required <- 3
  
  # Apply a time offset to the treatment time series
  # to account for the time it takes for odour to
  # arrive to the chambers
  # Units in seconds
  delay <- 0
  
  
  #### Probably you dont want to change this
  #### Please change these numbers only if you know what you are doing
  
  # Define a distance from the center of the chamber
  # to the decision zone
  # Units in mm
  border_mm <- 5
  
  # Behavioral masking
  # Ignore exits happening this amount of seconds
  # after the previous exit
  # to avoid counting the same exit 
  # as two exits happening within ridiculously little time  
  mask_duration <- 0.5
  
  ##################################################
  # CAUTION!! DONT CHANGE ANY CODE BELOW THIS LINE
  ##################################################
  
  treatments <- c(
    TREATMENT_A = treatment_A,
    TREATMENT_B = treatment_B
  )
  
  # src_file <- rstudioapi::getActiveDocumentContext()$path
  
  # expect syntax warning
  expect_warning({
    p1 <- idocr(experiment_folder = experiment_folder,
              treatments = treatments,
              border_mm = border_mm,
              min_exits_required = min_exits_required,
              # src_file = src_file,
              subtitle = description,
              delay = delay,
              mask_duration = mask_duration
    )}
  )
  
  
  vdiffr::expect_doppelganger("legacy_main", p1$gg)
  expect_snapshot_value(
    p1$pi, 
    style = "serialize", cran = FALSE
  )
  
  # expect deprecation warning
  expect_message({
    export_summary(experiment_folder = experiment_folder)
  })
  
})