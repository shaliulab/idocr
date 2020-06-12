import datetime
import json
import os
import logging

import yaml

logging.basicConfig(level=logging.INFO)

class IDOCConfiguration(object):
    '''
    Handles the idoc configuration parameters
    Data are stored in and retrieved from a JSON configuration file
    '''

    _settings = {

        'default_class': {
            'board': "ArduinoDummy",
            'camera': "OpenCVCamera",
            'drawer': "DefaultDrawer",
            'result_writer': "CSVResultWriter",
            'roi_builder': "IDOCROIBuilder",
            'tracker': "AdaptiveBGModel"
        },

        'core' : {
            'debug': True
        },

        'network': {

            'port': 9000
        },

        'folders' : {
                        'results' : {'path' : '/1TB/Cloud/Data/idoc_data/results', 'description' : 'Where data will be saved by the saver class.'},
                        'temporary' : {'path' : '/ethoscope_data/results', 'description' : 'A temporary location for downloading data.'},
                        'paradigms': {'path': '/1TB/Cloud/Lab/Gitlab/idoc/py_src/paradigms', 'description' : 'Where csv files containing hardware programs are stored.'}
        },

        'users' : {
                      'admin' : { # pylint: disable=bad-continuation
                          'id' : 1, 'name' : 'admin', 'fullname' : '', 'PIN' : 9999, 'email' : '',
                          'telephone' : '', 'group': '', 'active' : False, 'isAdmin' : True,
                          'created' : datetime.datetime.now().timestamp()
                      }
        },

        'roi_builder': {
            'args': (),
            'kwargs': {}
        },

        'io': {
            'result_writer': {
                'args': (),
                'kwargs': {
                    'max_n_rows_to_insert': 1,
                }
            },

            'camera': {
                'args': (),
                'kwargs': {
                    'framerate': 20, 'exposure_time': 50000,
                    'resolution': (960, 720),
                    'drop_each': 1,
                    'use_wall_clock': True,
                    'wrap': False
                }
            }
        },

        'controller': {
            'mapping_path': '/1TB/Cloud/Lab/Gitlab/idoc/py_src/mappings/mega.csv',
            'paradigm_path': 'unittest_long.csv',
            'arduino_port': "/dev/ttyACM0",
            'pwm': {
            },
        },

        'drawer': {
            'args': (),
            'kwargs': {
                'draw_frames': False,
                'video_out_fourcc': "DIVX",
                'framerate': None # match that of the camera
            },
            'last_drawn_path': "/tmp/last_img.png",
            'last_annot_path': "/tmp/last_img_annot.png",
        },

        'experiment': {
            'adaptation_time': 600,
            "max_duration": 3600,
            "location": None
        }
    }


    def __init__(self, config_file="/etc/idoc.conf"):
        self._config_file = config_file
        self._config_file_yaml = config_file.replace("conf", "yaml")
        self.load()

    @property
    def content(self):
        return self._settings

    @property
    def file_exists(self):

        return os.path.exists(self._config_file)

    def save(self):
        """
        Save settings to default json file
        """

        try:
            with open(self._config_file, 'w') as json_data_file:
                json.dump(self._settings, json_data_file)

            with open(self._config_file_yaml, 'w') as yaml_data_file:
                yaml.dump(self._settings, yaml_data_file)

            logging.info('Saved idoc configuration file to %s', self._config_file)

        except:
            raise ValueError('Problem writing to file % s' % self._config_file)

    def load(self):
        '''
        Reads saved configuration folders settings from json configuration file
        If file does not exist, creates default settings
        '''

        if not self.file_exists:
            self.save()

        else:
            try:
                with open(self._config_file, 'r') as json_data_file:
                    self._settings.update(json.load(json_data_file))
            except:
                raise ValueError("File %s is not a valid configuration file" % self._config_file)

        return self._settings


if __name__ == "__main__":
    config = IDOCConfiguration()
    config.save()
