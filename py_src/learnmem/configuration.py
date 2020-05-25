import os, json, datetime
import logging

class LearnMemConfiguration(object):
    '''
    Handles the learnmem configuration parameters
    Data are stored in and retrieved from a JSON configuration file
    '''

    _settings = {
        'core' : {
            'debug': True
        },

        'network': {

            'port': 9000
        },

        'folders' : {
                        'results' : {'path' : '/learnmem_data/results', 'description' : 'Where tracking data will be saved by the backup daemon.'},
                        'video' : {'path' : '/learn_mem/videos', 'description' : 'Where video chunks (h264) will be saved by the backup daemon'},
                        'temporary' : {'path' : '/ethoscope_data/results', 'description' : 'A temporary location for downloading data.'},
                        'programs': {'path': '/1TB/Cloud/Lab/Gitlab/learnmem/py_src/programs', 'description' : 'Where csv files containing hardware programs are stored.'}
        },

        'users' :   {
                        'admin' : {'id' : 1, 'name' : 'admin', 'fullname' : '', 'PIN' : 9999, 'email' : '', 'telephone' : '', 'group': '', 'active' : False, 'isAdmin' : True, 'created' : datetime.datetime.now().timestamp() }
        },

        'io': {
            #'max_n_rows_to_insert': 30000
            'max_n_rows_to_insert': 1
        },

        'arena': {
            'min_area': 1000, 'block_size': 9, 'param1': 13, 'kernel_factor': 5, 'rangelow': 0, 'rangeup': 255,
            'targets': 20, 'columns': 2, 'width': 65, 'height': 12
        },

        'fly': {
                'min_length': 2, 'min_dist_arena': 1, 'max_area': 30, 'min_area': 10, 'min_intensity': 20
        },

        'tracker': {
            'fps': 10, 'experimenter': 'Sayed', 'crop': 1, 'N': 10, 'fail': 'failed_arenas/'
        },

        'controller': {
            'board': 'ArduinoMega',
            'mapping_path': '/1TB/Cloud/Lab/Gitlab/learnmem/py_src/mappings/mega.csv'
        },

        'saver': {
            'video_format': "avi",
            'framerate': 5,
            'resolution': (1280, 960)
        },

        'pwm': {
            'ONBOARD_LED': 0.99999,
            'MAIN_VALVE' : 0.99999,
            'VACUUM': 0.99999
        },

        # TODO Sort this stuff
        'experiment': {
            "fraction_area":  1,
            "answer":  "Yes",
            "odor_A":  'A',
            "odor_B":  'B',
            "save_results_answer":  'Yes',
            "record_start":  0,
            "adaptation_time_minutes":  0,
            "decision_zone_mm": 10,
            "min_exits_required": 5,
            "max_time_minutes": 60,
            "sampling_rate": 50
        }
    }


    def __init__(self, config_file="/etc/learnmem.conf"):
        self._config_file = config_file
        self.load()

    @property
    def content(self):
        return self._settings

    @property
    def file_exists(self):
        '''
        '''
        return os.path.exists(self._config_file)

    def save(self):
        '''
        Save settings to default json file
        '''
        try:
            with open(self._config_file, 'w') as json_data_file:
                json.dump(self._settings, json_data_file)

            logging.info('Saved ethoscope configuration file to %s' % self._config_file)

        except:
            raise ValueError ('Problem writing to file % s' % self._config_file)

    def load(self):
        '''
        Reads saved configuration folders settings from json configuration file
        If file does not exist, creates default settings
        '''

        if not self.file_exists : self.save()

        else:
            try:
                with open(self._config_file, 'r') as json_data_file:
                    self._settings.update ( json.load(json_data_file) )
            except:
                raise ValueError("File %s is not a valid configuration file" % self._config_file)

        return self._settings
