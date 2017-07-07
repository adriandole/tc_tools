from typing import Union

import visa
import time
import logging
from tc_tools.utils import is_number


class VISAInstrument:
    """Wrapper for PyVisa instruments"""

    def __init__(self, address: str):
        """
        Gets a VISA instrument from a resource manager

        :param address: VISA address of the instrument
        """
        resource_manager = visa.ResourceManager()
        self._visa_ref =\
            (resource_manager.
             open_resource(address)) # type: visa.resources.Resource


class PRT(VISAInstrument):
    """Hart Scientific PRT"""

    logger = logging.getLogger('PRT')

    def __init__(self, address: str) -> None:
        """
        Calls the super constructor and sets the units to C

        :param address: VISA address of the instrument
        """
        super(PRT, self).__init__(address)
        self.set_units('C')

    def get_temp(self) -> float:
        """Reads the temperature"""
        time.sleep(1)
        self._visa_ref.clear()
        time.sleep(1)
        read = self._visa_ref.query('READ?')
        # Portion of the output with temperature digits
        temp_portion = read[5:11]
        if not (is_number(temp_portion) and (float(temp_portion) > 0)):
            self.logger.warning('Bad reading from PRT')
            raise IOError
        return float(temp_portion)

    def set_units(self, units: str):
        """
        Changes the output units

        :param units: temperature units; C, K, or F
        """
        valid_units = ['C', 'K', 'F']
        units = units.upper()
        if units in valid_units:
            # Sleep before writing prevents quick sequential writes,
            # which may cause errors
            time.sleep(1)
            self._visa_ref.write('UNIT:TEMP {}'.format(units))
            self.logger.info('Units set to {}'.format(units))


class DAQ(VISAInstrument):
    """Agilent 34970A"""

    logger = logging.getLogger('DAQ')

    def __init__(self, address: str):
        """
        Calls the super constructor and initializes a field

        :param address: VISA address of the instrument
        """
        super(DAQ, self).__init__(address)
        self.channels_set = False
        self.channels = []
        self.calibrated = False
        self.cal_functions = {}
        self._configured_channels = {}

    def set_channels(self, channels: list, units: str = 'C'):
        """
        Sets the channels to read from

        :param channels: channels to read as a list
        :param units: temperature units; C, K, or F
        """
        self.channels = channels
        str_channels = ','.join(channels)
        for channel in channels:
            self.cal_functions.update({channel: lambda x: x})
            self._configured_channels.update({channel: False})
        time.sleep(1)
        type_config = 'CONF:TEMP TC,T,(@{})'.format(str_channels)
        self._visa_ref.write(type_config)
        self.logger.info('Config written: {}'.format(type_config))

        time.sleep(1)
        read_config = 'SENS:TEMP:TRAN:TC:RJUN:TYPE FIX,(@{})'.format(
            str_channels)
        self._visa_ref.write(read_config)
        self.logger.info('Config written: {}'.format(read_config))

        valid_units = ['C', 'K', 'F']
        units = units.upper()
        if units in valid_units:
            time.sleep(1)
            unit_config = 'UNIT:TEMP {},(@{})'.format(units, str_channels)
            self._visa_ref.write(unit_config)
            self.logger.info('Config written: {}'.format(unit_config))
        else:
            self.logger.warning('Invalid units entered. Using system default.')

        self.logger.info('Channels set to: {}'.format(channels))
        self.channels_set = True

    def get_temp_uncalibrated(self, as_dict = False) -> Union[list, dict]:
        """
        Reads the set channels without calibration

        :return: temperature readings, ordered by channel
        """
        if self.channels_set:
            self._visa_ref.clear()
            time.sleep(1)
            data = self._visa_ref.query_ascii_values('READ?')
            if not all(0 < n < 100 for n in data):
                self.logger.warning('Bad readings')
                raise IOError('DAQ read error')
            self.logger.warning('Reading uncalibrated temperatures')
            if not as_dict:
                return data
            else:
                return_dict = {}
                for n in range(len(self.channels)):
                    return_dict.update({self.channels[n]: data[n]})
                return return_dict
        else:
            raise UserWarning('Set DAQ channels before reading data')

    def set_calibration(self, channel: int, gain: float = 1.0,
                        offset: float = 0.0):
        """
        Sets calibration constants for a given channel

        :param channel:
        :param gain:
        :param offset:
        """
        self.cal_functions.update({channel: lambda x: gain*x + offset})

    def get_calibrated_temp(self, as_dict=True) -> Union[dict, list]:
        """
        Reads temperatures and applies calibration

        :param as_dict: whether to return as a dict
        :return: dict or list of return values
        """
        data = self.get_temp_uncalibrated(as_dict=True)
        output = {}
        for channel in self.channels:
            output.update({channel: self.cal_functions[channel](data[channel])})
        if as_dict:
            return output
        else:
            output_list = []
            for x in output.items():
                output_list.append(x[1])
            return output_list


class TCBath(VISAInstrument):
    """Thermo AC25 bath"""

    logger = logging.getLogger('Bath')

    def start(self):
        """Starts the bath"""
        time.sleep(1)
        self._visa_ref.write('W GO 1')
        self.logger.info('Bath started')

    def stop(self):
        """Stops the bath"""
        time.sleep(1)
        self._visa_ref.write('W RR -1')
        self.logger.info('Bath stopped')

    def set_temp(self, temp: float):
        """Sets the temperature setpoint"""
        time.sleep(1)
        self._visa_ref.write('W SP {:.2f}'.format(temp))
        self.logger.info('Bath set to {}C'.format(temp))

    def get_temp(self) -> float:
        """Reads the current temperature"""
        time.sleep(1)
        read = self._visa_ref.query('R T1')
        try:
            if len(read) > 5:
                temp_portion = read[3:-4]
            if is_number(temp_portion):
                return float(temp_portion)
        except:
            self.logger.warning('Bad readings')


class PowerMeter(VISAInstrument):
    """Yokogawa power meter"""

    logger = logging.getLogger('Power Meter')
    measure_commands = ['MEAS:NORM:ITEM:PRES CLE', 'MEAS:NORM:ITEM:{}:ELEMENT1',
                        'ON']

    def reset_integration(self):
        """Resets the power integration"""
        time.sleep(0.1)
        self._visa_ref.write('INTEG:RESET')
        self.logger.info('Integration reset')

    def start_integration(self):
        """Starts the power integration"""
        time.sleep(0.1)
        self._visa_ref.write('INTEG:START')
        self.logger.info('Integration started')

    def stop_integration(self):
        """Stops the power integration"""
        time.sleep(0.1)
        self._visa_ref.write('INTEG:STOP')
        self.logger.info('Integration stopped')

    def _read_sequence(self, value: str) -> float:
        self.measure_commands[1] = self.measure_commands[1].format(value)
        for command in self.measure_commands:
            time.sleep(0.1)
            self._visa_ref.write(command)
        return self._visa_ref.query_ascii_values('MEAS:NORM:VAL?')

    def read_volts(self) -> float:
        """Reads instantaneous voltage"""
        return self._read_sequence('V')

    def read_watts(self) -> float:
        """Reads power"""
        return self._read_sequence('W')

    def read_amps(self) -> float:
        """Reads current"""
        return self._read_sequence('A')

    def read_energy(self) -> float:
        """Reads energy from power integration"""
        return self._read_sequence('WH')


class Solenoid:
    """Controllable solenoid connected to the DAQ"""

    def __init__(self, parent: DAQ, channel: int):
        """
        Creates a solenoid object connected to a specific DAQ

        :param parent: DAQ object that this solenoid is connected to
        :param channel: DAQ channel the solenoid is connected to
        """
        self.parent = parent
        self.channel = channel
        self.logger = logging.getLogger('Solenoid @{}'.format(channel))

    def open(self):
        """Opens the solenoid"""
        self.parent._visa_ref.write('ROUT:OPEN (@{})'.format(self.channel))
        self.logger.info('Opened')

    def close(self):
        """Closes the solenoid"""
        self.parent._visa_ref.write('ROUT:CLOS (@{})'.format(self.channel))
        self.logger.info('Closed')