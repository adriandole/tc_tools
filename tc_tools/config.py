import configparser
import os
from typing import Union


def tc_calibration_config(file: Union[os.path.abspath, str]
                          = 'tc_calibration_config.ini') -> \
        configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    if not os.path.isfile(file):
        print("Creating new calibration config file")
        config_file = open(file, 'w')
        cfg['Files'] = {'output file': 'cal_data.csv', 'headers': 'channels'}
        cfg["Instruments"] = {'PRT address': 'ASRL1:INSTR',
                              'DAQ address': 'GPIB0::9::INSTR',
                              'bath address': 'COM4'}
        cfg['Procedure'] = {'set points': '5 15 25 35 45 55 65 75',
                            'channels': '101 102 103'}
        cfg.write(config_file)
        config_file.close()
    return cfg.read(file)

def valve_calibration_config(file: Union[os.path.abspath, str]
                             = 'valve_calibration_config.ini') -> \
    configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    if not os.path.isfile(file):
        print('Creating new valve calibration config file')
        config_file = open(file, 'w')
        cfg['Files'] = {'output file': 'valve_cal.csv'}
        cfg['Instruments'] = {'DAQ address': 'GPIB0::9::INSTR',
                              'draw solenoid channel': '101',
                              'weigh solenoid channel': '101',
                              'flow valve channel': '101'}
        cfg['Procedure'] = {'set points': '1 2 3 4 5 6 7 8 9 10'}
        cfg.write(config_file)
        config_file.close()
    return cfg.read(file)


def doe_test_config(file: Union[
    os.path.abspath, str] = 'doe_test_config.ini') -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    if not os.path.isfile(file):
        print('Creating new valve calibration config file')
        config_file = open(file, 'w')
        cfg['Files'] = {'output file': '', 'draw data file': '',
                        'schedule file': '', 'draw headers': '',
                        'data headers': ''}
        cfg['Instruments'] = {'DAQ address': 'GPIB0::9::INSTR',
                              'power meter address': 'ASRL1::INSTR'}
        cfg['Channels'] = {'tank thermocouples': '', 'tank inlet': '',
                           'tank outlet': '', 'scale': '', 'weigh tank': '',
                           'flow valve': '', 'rh sensor': ''}
        cfg.write(config_file)
        config_file.close()
    return cfg.read(file)