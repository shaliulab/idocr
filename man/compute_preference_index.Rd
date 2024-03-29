% Generated by roxygen2: do not edit by hand
% Please edit documentation in R/preference.R
\name{compute_preference_index}
\alias{compute_preference_index}
\title{Compute the preference index displayed by the animals in a dataset}
\usage{
compute_preference_index(annotated_data, min_exits_required = 5)
}
\arguments{
\item{annotated_data}{data.frame where every row captures the position of one animal at ome timepoint
when the animal exists the decision zone and a sign (type) is associated with the exit (appetitive or aversive).
Must contain fields t, side, type, region_id}

\item{min_exits_required}{Minimum number of exists required
when computing the preference index. Animals not reaching this number of exits
are not considered in the analysis}
}
\description{
Compute the preference index displayed by the animals in a dataset
}
