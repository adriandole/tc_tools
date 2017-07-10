import visa
import os
import csv
import time
import logging
import numpy as np
from datetime import datetime
from tc_tools.instruments import PRT, DAQ


def address_query():
    """Sends an *IDN? query to each port. Each instrument should return its name."""
    resource_manager = visa.ResourceManager()
    addresses = resource_manager.list_resources()

    for address in addresses:
        print(address)
        try:
            instrument = resource_manager.open_resource(address)
            print(instrument.query('*IDN?'))
        except:
            print('Read error\n')

    resource_manager.close()


class DataWriter:
    """Writes input data to a file"""

    logger = logging.getLogger('Calibration Data')

    def __init__(self, output_file_name: os.path.abspath, headers: list):
        """
        Sets the file name and headers

        :param output_file_name: path to output to
        :param headers: headers for the CSV file
        """
        self.headers = ['Time', 'PRT'] + headers
        self.output_file_path = os.path.abspath(output_file_name)
        self.logger.info('Writing to: {}'.format(str(self.output_file_path)))
        self.file_already_exists = os.path.isfile(self.output_file_path)
        self._open_file()
        self.csv_writer = csv.writer(self.output_file, dialect='excel',
                                     quoting=csv.QUOTE_ALL)
        if not self.file_already_exists:
            self.csv_writer.writerow(self.headers)
            self.logger.info('Writing CSV headers')

    def _open_file(self):
        if self.file_already_exists:
            self.output_file = open(self.output_file_path, 'a', newline='')
            self.logger.info('Appending to existing file')
        else:
            self.output_file = open(self.output_file_path, 'w', newline='')
            self.logger.info('Creating new file')

    def _write(self, input_data):
        self.csv_writer.writerow([datetime.now().strftime('%Y-%m-%d %H:%M:%S')] + input_data)


class CalibrationWriter(DataWriter):
    """Writer for the calibration procedure"""

    def collect_data(self, prt: PRT, daq: DAQ, reads:int=10, interval:int=30):
        """
        Collects data from the given instrument objects

        :param prt: the PRT thermometer to read from
        :param daq: the DAQ to read from
        :param reads: how many readings to take
        :param interval: time interval between readings in seconds
        """
        successful_reads = 0
        self.logger.info('Collecting data: {} readings at {}s intervals'
                         .format(reads, interval))
        while successful_reads < reads:
            try:
                data = [prt.get_temp()] + daq.get_temp_uncalibrated()
                self._write(data)
                successful_reads += 1
                self.logger.info('Read #{} successful'.format(successful_reads))
            except:
                self.logger.warning('DAQ read error. Retrying')
                continue
            time.sleep(interval)
        self.logger.info('Data collection complete.')
        self.output_file.flush()


def steady_state_monitor(prt: PRT, steady_delta:float=0.1):
    """
    Uses the given PRT to monitor if the bath is steady-state

    :param prt: the PRT to monitor with
    :param steady_delta: maximum temperature difference over ten minutes
    """
    temperature_array = np.empty((0, 0))
    steady_state = False
    while not steady_state:
        try:
            recent_temp = prt.get_temp()
        except:
            continue
        print(recent_temp, end='\r')
        temperature_array = np.append(temperature_array, recent_temp)
        if temperature_array.size > 60:
            temperature_array = np.delete(temperature_array, 0)
        delta = np.amax(temperature_array) - np.amin(temperature_array)
        steady_state = (delta <= steady_delta) and (temperature_array.size >= 60)
        time.sleep(10)
        if steady_state:
            return True
