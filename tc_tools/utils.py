import csv
import os
import re
from collections import namedtuple
from datetime import datetime, timedelta
from typing import List

import numpy as np

from tc_tools.instruments import *


def address_query():
    """Sends an *IDN? query to each port. Each instrument should return its
    name."""
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

    def __init__(self, output_file_path: os.path.abspath, headers: list):
        """
        Sets the file name and headers

        :param output_file_name: path to output to
        :param headers: headers for the CSV file
        """
        self.headers = ['Time'] + headers
        self.output_file_path = output_file_path
        self.start = time.time()
        self.logger.info('Writing to: {}'.format(str(self.output_file_path)))
        self.file_already_exists = os.path.isfile(self.output_file_path)
        self._open_file()
        self.csv_writer = csv.writer(self.output_file, dialect='excel',
                                     quoting=csv.QUOTE_ALL)
        if not self.file_already_exists:
            self.csv_writer.writerow(self.headers)
            self.logger.info('Writing CSV headers')

    def clock_reset(self):
        self.start = time.time()

    def _open_file(self):
        if self.file_already_exists:
            self.output_file = open(self.output_file_path, 'a', newline='')
            self.logger.info('Appending to existing file')
        else:
            self.output_file = open(self.output_file_path, 'w', newline='')
            self.logger.info('Creating new file')

    def _write(self, input_data):
        self.csv_writer.writerow([datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
                                 + input_data)


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


class SimulatedUseWriter(DataWriter):
    """Writer for the simulated use test"""

    def __init__(self, headers: List[str], output_file: os.path.abspath,
                 daq: DAQ, rh: HumiditySensor, power_meter: PowerMeter):
        """
        Writer for minutely data during the simulated use test

        :param headers: column titles for the output file
        :param output_file: path to the output file
        :param daq: DAQ to read from
        :param rh: humidity sensor object
        :param power_meter: power meter object
        """
        super(SimulatedUseWriter, self).__init__(output_file, headers)
        self.daq = daq
        self.rh = rh
        self.pm = power_meter
        self.recording = True
        self.drawing = False

    def gather_data(self, interval: int = 60):
        """
        Gathers data until stopped

        :param interval: seconds to wait between reads
        """
        while self.recording:
            self.read_data()
            time.sleep(interval)

    def read_data(self):
        """Reads all relevant data"""
        tc_data = self.daq.get_calibrated_temp()
        power_data = [self.pm.read_watts(),
                      self.pm.read_energy(), self.pm.read_volts(),
                      self.pm.read_amps()]
        rh_data = [self.rh.rh()]
        all_data = [time.time() - self.start] + [self.drawing] + tc_data +\
                   rh_data + power_data
        self._write([str(n) for n in all_data])

    def set_drawing(self, drawing: bool):
        """Tells the writer if there's current a draw"""
        self.drawing = drawing

    def stop_data(self):
        """Terminates any running recording"""
        self.recording = False


class DrawWriter(DataWriter):
    """Writer for draws"""

    def __init__(self, headers: List[str], output_file: os.path.abspath,
                 inlet_channel: int, outlet_channel: int, daq: DAQ,
                 scale: MTScale):
        """
        Creates a writer for use while drawing water

        :param headers: column titles for the output file
        :param output_file: path to the output file
        :param inlet_channel: channel of the tank inlet thermocouple
        :param outlet_channel: channel of the tank outlet thermocouple
        :param daq: DAQ to read from
        :param scale: scale object
        """
        super(DrawWriter, self).__init__(output_file, headers)
        self.daq = daq
        self.scale = scale
        self.inlet = inlet_channel
        self.outlet = outlet_channel
        self.start = time.time()
        self.draw_num = 1

    def read_data(self, initial: bool = False):
        """Reads relevant data"""
        temps = self.daq.get_calibrated_temp(as_dict=True)
        elapsed = 0 if initial else [self.start - time.time()]
        temp_data = [temps[self.inlet] + temps[self.outlet]]
        weight = [self.scale.weigh()]
        self._write(elapsed + temp_data + weight)

    def set_draw_num(self, draw_num: int):
        self.draw_num = draw_num

    def reset(self):
        """Resets the start time"""
        self.start = time.time()

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


def parse_schedule(schedule_file: os.path.abspath) -> namedtuple:
    """
    Reads the draw schedule from a file

    :param schedule_file: path to the schedule file
    :return: tuple of draw parameters
    """
    schedule = namedtuple('schedule', ['time', 'volume', 'rate'])
    with open(schedule_file) as f:
        reader = csv.reader(f, dialect='excel')
        time = []
        volume = []
        rate = []
        for row in reader:
            h,m = re.split(':', row[0])
            time += [timedelta(hours=int(h), minutes=int(m)).total_seconds()]
            volume += [float(row[1])]
            rate += [float(row[2])]

    return schedule(time, volume, rate)

