import subprocess

class call2R:

    def __init__(self, experiment_folder, decision_zone_mm=10, min_exits_required=5, max_time_minutes=60):

        self.experiment_folder = experiment_folder
        self.decision_zone_mm = decision_zone_mm
        self.min_exits_required = min_exits_required
        self.max_time_minutes = max_time_minutes

    def run(self):
        subprocess.call(['R', '--slave', '-e', 'LeMDTr::preprocess_and_plot( \
            experiment_folder = "{}", \
            decision_zone_mm = {}, \
            min_exits_required = {}, \
            max_time_minutes = {} \
            )'.format(self.experiment_folder, self.decision_zone_mm, self.min_exits_required, self.max_time_minutes)])


