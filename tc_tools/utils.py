import visa
import os
import csv
import time
import numpy as np
from datetime import datetime


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


class TempWriter:
    """Writes data to a file"""
    def __init__(self, output_file_name, headers):
        """
        Sets the file name and headers

        :param output_file_name: path to output to
        :type output_file_name: str
        :param headers: headers for the CSV file
        :type headers: list
        """
        self.headers = ['Time', 'PRT'] + headers
        self.output_file_name = output_file_name
        self.file_already_exists = os.path.isfile(self.output_file_name)
        self._open_file()
        self.csv_writer = csv.writer(self.output_file, dialect='excel', quoting=csv.QUOTE_ALL)
        if not self.file_already_exists:
            self.csv_writer.writerow(self.headers)

    def collect_data(self, prt, daq, reads=10, interval=30):
        """
        Collects data from the given instrument objects

        :param prt: the PRT thermometer to read from
        :type prt: tc_tools.instruments.PRT
        :param daq: the DAQ to read from
        :type daq: tc_tools.instruments.DAQ
        :param reads: how many readings to take
        :type reads: 10
        :param interval: time interval between readings in seconds
        :type interval: int
        """
        successful_reads = 0
        while successful_reads < reads:
            try:
                data = [prt.get_temp()] + daq.get_temp()
                self._write(data)
                successful_reads += 1
                print('Read #{} successful'.format(successful_reads))
            except:
                print('DAQ read error. Retrying')
                continue
            time.sleep(interval)
        print('Data collection complete.')
        self.output_file.flush()

    def _open_file(self):
        if self.file_already_exists:
            self.output_file = open(self.output_file_name, 'a', newline='')
        else: 
            self.output_file = open(self.output_file_name, 'w', newline='')

    def _write(self, input_data):
        self.csv_writer.writerow([datetime.now().strftime('%Y-%m-%d %H:%M:%S')] + input_data)


def steady_state_monitor(prt, steady_delta=0.1):
    """
    Uses the given PRT to monitor if the bath is steady-state
    :param prt: the PRT to monitor with
    :type prt: tc_tools.instruments.PRT
    :param steady_delta: maximum temperature difference over ten minutes
    :type steady_delta: float
    """
    temperature_array = np.empty((0, 0))
    steady_state = False
    while not steady_state:
        try:
            recent_temp = prt.get_temp()
        except:
            continue
        print('Temperature: {}'.format(recent_temp))
        temperature_array = np.append(temperature_array, recent_temp)
        if temperature_array.size > 60:
            temperature_array = np.delete(temperature_array, 0)
        delta = np.amax(temperature_array) - np.amin(temperature_array)
        steady_state = (delta <= steady_delta) and (temperature_array.size >= 60)
        print('Steady state: {}\nDelta: {:.3f}'.format(steady_state, delta))
        time.sleep(10)
        if steady_state:
            return True


def is_number(s):
    """
    Returns if a given string input is a number

    :param s: the input to test
    :type s: str
    :return: if the input is a number
    :rtype: bool
    """
    try:
        float(s)
        return True
    except ValueError:
        return False