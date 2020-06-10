import subprocess
import os.path

class RSession():

    def __init__(self, experiment_folder=None, decision_zone_mm=10, min_exits_required=5, max_time_minutes=60):

        self.experiment_folder = experiment_folder
        self.decision_zone_mm = decision_zone_mm
        self.min_exits_required = min_exits_required
        self.max_time_minutes = max_time_minutes

    def run(self):
        subprocess.call(['nautilus', self.experiment_folder])

        cmd = ['R', '--slave', '-e', 'lemdt_analysis <- LeMDTr::BehaviorAnalyzer$new( \
            experiment_folder = "{}", \
            decision_zone_mm = {}, \
            min_exits_required = {}, \
            max_time_minutes = {} \
            )\nlemdt_analysis$run()'.format(self.experiment_folder, self.decision_zone_mm, self.min_exits_required, self.max_time_minutes)]
        
        readable_cmd = ' '.join(cmd[3:])
        readable_cmd = ' '.join(readable_cmd.split())

        handle = open(os.path.join(self.experiment_folder, "script.R"), 'w')
        handle.write(readable_cmd + '\n')
        handle.close()
        subprocess.call(cmd)


