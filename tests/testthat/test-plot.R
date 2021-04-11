test_that("base plot produces plot with correct axes and facet", {
  
  tracker_data <- toy_tracker_small()
  limits <- c(-100, 100)
  tracker_data$facet <- paste0("ROI_", tracker_data$region_id)
  gg <- base_plot(tracker_data, limits)
  
  expect_equal(gg$scales$scales[[1]]$limits, c(-60, 0))
  expect_equal(gg$scales$scales[[2]]$limits, limits)
  vdiffr::expect_doppelganger("base-plot", gg)
  
  limits <- c(-50, 50)
  tracker_data$facet <- paste0("ROI_", tracker_data$region_id)
  gg <- base_plot(tracker_data, limits)
  expect_equal(gg$scales$scales[[2]]$limits, limits)
  
})


test_that("mark stimuli renders stimuli as rectangles in the plot", {

  rectangles <- toy_rectangle_data()
  gg <- ggplot()# + theme_void()
  colors = c("TREATMENT_A" = "red", "TREATMENT_B" = "blue")
  gg <- mark_stimuli(gg, rectangles, colors, names(colors))
  gg <- gg +
    scale_x_continuous(limits = c(-100, 100)) +
    scale_y_continuous(limits=c(10, 0), trans = scales::reverse_trans())
  
  vdiffr::expect_doppelganger("event-rectangles", gg)
})

test_that("mark decision zone produces a vertical line on the plots", {
  
  gg <- ggplot() + scale_x_continuous(limits=c(-100, 100))
  border <- 20
  gg <- mark_decision_zone(gg, border)
  vdiffr::expect_doppelganger("decision-zone-20", gg)

  gg <- ggplot() + scale_x_continuous(limits=c(-100, 100))
  border <- 50
  gg <- mark_decision_zone(gg, border)
  vdiffr::expect_doppelganger("decision-zone-50", gg)
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
  gg <- mark_crosses(gg, crossing_data)
  vdiffr::expect_doppelganger("mark-crosses", gg)
  
  gg <- ggplot()
  crossing_data$x <- crossing_data$x * -1
  gg <- mark_crosses(gg, crossing_data)
  vdiffr::expect_doppelganger("mark-crosses-flip", gg)
})


test_that("save plot saves both pdf and png with the right file size", {
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

  # check their expected size
  expect_equal(file.size(pdf_file), 5098)
  expect_equal(file.size(png_file), 914)
})

test_that("document_plot annotates the plot", {
  
  gg <- ggplot()
  gg <- document_plot(gg, subtitle = "A subtitle")
  vdiffr::expect_doppelganger("document-plot", gg)
})
