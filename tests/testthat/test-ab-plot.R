test_that("base plot produces plot with correct axes and facet", {
  
  tracker_data <- toy_tracker_small()
  limits <- c(-100, 100)
  tracker_data$facet <- paste0("ROI_", tracker_data$region_id)
  gg <- base_plot(tracker_data, limits, nrow=1, ncol=2) + labs(
  subtitle = "y axis should run downard. Plot should have two faces, one per animal"
  )
  
  expect_equal(gg$scales$scales[[1]]$limits, c(-60, 0))
  expect_equal(gg$scales$scales[[2]]$limits, limits)
  # vdiffr::expect_doppelganger("ab-plot_base-plot", gg)
  
  limits <- c(-50, 50)
  tracker_data$facet <- paste0("ROI_", tracker_data$region_id)
  gg <- base_plot(tracker_data, limits, nrow=1, ncol=2)
  expect_equal(gg$scales$scales[[2]]$limits, limits)
})

# uncomment when vdiffr supports testthat version 3
test_that("mark time works", {
  tracker_data <- toy_tracker_small()
  gg <- ggplot()
  data <- data.frame(t = seq(0, 900, 5), x = 1:181)
  gg <- mark_time(data = data, gg = gg, freq = 60, downward = TRUE) + labs(
    subtitle = "y axis should run downard with one tick every minute (60 s)"
  )
  # vdiffr::expect_doppelganger("ab-plot_mark-time", gg)
  
  gg <- mark_time(data = data, gg = gg, freq = 120, downward = TRUE) + labs(
    subtitle = "y axis should run downard with one tick every 2 minutes (120 s)"
  )
  
  # vdiffr::expect_doppelganger("ab-plot_mark-time-custom-freq", gg)

  gg <- mark_time(data = data, gg = gg, freq = 120, downward = FALSE)  + labs(
    subtitle = "y axis should run upward with one tick every 2 minutes (120 s)"
  )
  
  # vdiffr::expect_doppelganger("ab-plot_mark-time-upward", gg)
})

test_that("mark stimuli renders stimuli as rectangles in the plot", {

  rectangles <- toy_rectangle_data()
  gg <- ggplot()# + theme_void()
  colors = c("TREATMENT_A" = "red", "TREATMENT_B" = "blue")
  gg <- mark_stimuli(gg, rectangles, colors, names(colors))
  gg <- gg +
    scale_x_continuous(limits = c(-100, 100)) +
    scale_y_continuous(limits=c(10, 0), trans = scales::reverse_trans()) +
    labs(subtitle = "Plot should have a red and blue checker pattern. 
         First row runs from 1-3 mins and has TREATMENT_A_LEFT & B_RIGHT.
         Second row runs from 3-5 mins and has a flipped pattern
         ")
  
  # vdiffr::expect_doppelganger("ab-plot_event-rectangles", gg)
})

test_that("mark decision zone produces a vertical line on the plots", {
  
  gg <- ggplot() + scale_x_continuous(limits=c(-100, 100))
  border <- 20
  gg <- mark_decision_zone(gg, border) +
    labs(subtitle = "Decision zone should be visible by dashed vertical lines at 20/-20")
  # vdiffr::expect_doppelganger("ab-plot_decision-zone-20", gg)

  gg <- ggplot() + scale_x_continuous(limits=c(-100, 100))
  border <- 50
  gg <- mark_decision_zone(gg, border)
  # vdiffr::expect_doppelganger("ab-plot_decision-zone-50", gg)
})

test_that("mark crosses produces marks that are visible and accurate", {
  
  border <- 20
  crossing_data <- toy_cross_data()
  crossing_data_extra <- toy_cross_data()
  crossing_data_extra$t <- crossing_data_extra$t + 10
  crossing_data_extra$side <- crossing_data_extra$side * -1
  
  crossing_data <- rbind(
    crossing_data,
    crossing_data_extra
  )
  crossing_data$type <- c("appetitive", "aversive")[c(1,1,2,2,1,1,2,2,1,1)]
  crossing_data$x <- crossing_data$side * border
  
  gg <- ggplot()
  gg <- mark_crosses(gg, crossing_data) + labs(
    subtitle = "x..xx / ..x.."
  )
  # vdiffr::expect_doppelganger("ab-plot_mark-crosses", gg)
  
  gg <- ggplot()
  crossing_data$x <- crossing_data$x * -1
  gg <- mark_crosses(gg, crossing_data) +
    labs(subtitle = "..x.. / x..xx")
  # vdiffr::expect_doppelganger("ab-plot_mark-crosses-flip", gg)
})


test_that("save_plot saves both pdf and png", {
  temp_dir <- tempdir()
  gg <- ggplot() + geom_point(aes(x=1:10, y=1:10), size=2, color="black") +
    scale_x_continuous(limits=c(0,10), breaks=1:10) +
    scale_y_continuous(limits=c(0,10), breaks=1:10)
  save_plot(gg, temp_dir, height=2, width=4)
  
  # the default plot name is DUMMY.ext
  pdf_file <- grep(pattern = "DUMMY.pdf", x = list.files(temp_dir, full.names = T), value = TRUE)
  png_file <- grep(pattern = "DUMMY.png", x = list.files(temp_dir, full.names = T), value = TRUE)
  
  # check the files exist
  expect_length(pdf_file, 1)
  expect_length(png_file, 1)
})


test_that("mark_analysis_mask works", {
  
  gg <- ggplot() + geom_point(aes(x=1:10, y=1:10), size=2, color="black") +
    scale_x_continuous(limits=c(0,10), breaks=1:10) +
    scale_y_continuous(limits=c(0,10), breaks=1:10)
  
  gg <- mark_analysis_mask(gg, analysis_mask = c(1, 5)) +
    labs(subtitle = "Analysis mask should be displayed from min 1-5")
  # vdiffr::expect_doppelganger("ab-plot_mark-analysis-mask", gg)
  
})

test_that("document_plot annotates the plot", {
  
  gg <- ggplot()
  gg <- document_plot(gg, subtitle = "A subtitle")
  # vdiffr::expect_doppelganger("ab-plot_document-plot", gg)
})
