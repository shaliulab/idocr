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


