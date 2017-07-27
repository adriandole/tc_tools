import configparser
import os
from typing import Union


def tc_calibration_config(file: Union[os.path.abspath, str]
                          = 'tc_calibration_config.ini') -> \
        configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    if not os.path.isfile(file):
        print("Creating new calibration config file")
        config_file = open('tc_calibration_config.ini', 'w')
        cfg['Files'] = {'output file': 'data.csv', 'headers': 'channels'}
        cfg["Instruments"] = {'PRT address': 'ASRL1:INSTR',
                              'DAQ address': 'GPIB0::9::INSTR',
                              'bath address': 'COM4'}
        cfg['Procedure'] = {'set points': '5 15 25 35 45 55 65 75',
                            'channels': '101 102 103'}
        cfg.write(config_file)
        config_file.close()
    return cfg.read(file)
