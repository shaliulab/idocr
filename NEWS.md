# idocr 1.1.0

* Test coverage reached of > 80% and Travis CI implemented.
* Summary outputs contain NA when no data is available, instead of just blank.
This helps avoid confusion between really missing data and program artifacts (which can always happen).
* export_summary is integrated into the main idocr::idocr entrypoint.
* treatments passed to idocr should be unnamed and match a stimulus listed in the CONTROLLER_EVENTS table.
* name of the treatment as shown in the plot is controlled via a new labels parameter in idocr::idocr.
* validation of CONTROLLER_EVENTS table to check for heterogeneous number of fields on each row.
A friendly error message is issued in that case with clear instructions on how to proceed.
* Implement plot_mask to totally ignore any data outside of the plot_mask, in seconds.
Ignored data is not considered for analysis nor plotting
* Implement analysis mask to ignore any data outside of the analysis_mask, in seconds.
Ignored data is not considered for analysis, but it is still plotted (i.e. a complete trace is shown).

# idocr 1.0.0

* Code reorganized into modules with well defined functionality.
* main.R script documented.
* Provide name of treatments shown in the legend via the `treatments` argument to `idocr::idocr`.
* Customise behavioral mask duration, decision zone, time offset for odour delivery, and number of exits required.
* Plot shows a break for every minute on the time axis.
* Script is saved in the experiment folder for documentation purposes.
* `export_summary` works by just providing an experiment folder, no need for an output_csv path.
* PI.csv contains preference index and also number of exits towards the apetitive and the aversive treatment,
  so one can easily manually check the computed index is correct.


