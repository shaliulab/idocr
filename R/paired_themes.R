TEXT_SIZE <- 12 # 20 becomes 20
TITLE_SIZE <- 15
LEGEND_TEXT_SIZE <- 15


#' @import ggplot2
#' @import ggprism
#' @export
get_sleep_plot_theme <- function() {
  ggprism::theme_prism() + ggplot2::theme(
    axis.text = ggplot2::element_text(size = TEXT_SIZE),
    axis.title = ggplot2::element_text(size = TITLE_SIZE),
    axis.text.y = ggplot2::element_text(size = TEXT_SIZE),
    strip.text = ggplot2::element_blank(),
    plot.tag = ggplot2::element_blank(),
    legend.key.width = unit(1, "null"),
    legend.text = ggtext::element_markdown(size = LEGEND_TEXT_SIZE)
  )
}

#' @import ggplot2
#' @export
get_paired_plot_theme <- function() {
  get_sleep_plot_theme() + theme(
    axis.title.x = ggplot2::element_blank(),
    axis.ticks.x = ggplot2::element_blank(),
    axis.text.x = ggplot2::element_blank(),
    axis.line.x = ggplot2::element_blank(),
    panel.spacing = unit(0, "npc"),
    panel.spacing.x = unit(0, "pt")
  )
}

#' @import ggplot2
#' @export
get_summary_plot_theme <- function() {
  get_paired_plot_theme() + ggplot2::theme(
    panel.spacing = unit(0, "npc")
  )
}

#' @import ggplot2
#' @export
get_traces_plot_theme <- function() {
  get_summary_plot_theme() + ggplot2::theme(
    axis.title.y = ggplot2::element_blank(),
    axis.text.x = ggplot2::element_text(size = TEXT_SIZE*0.8),
    axis.line.y = ggplot2::element_blank(),
    axis.ticks.length = unit(.05, "cm"),
    title = ggplot2::element_blank(),
    strip.text = ggplot2::element_blank(),
    panel.border = ggplot2::element_rect(colour = "black", fill = NA, linewidth = 1)
  )
}