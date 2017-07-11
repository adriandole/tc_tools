import logging
import time
from typing import Union

import visa


class VISAInstrument:
    """Wrapper for PyVisa instruments"""

    logger = logging.getLogger('VISA')

    def __init__(self, address: str):
        """
        Gets a VISA instrument from a resource manager

        :param address: VISA address of the instrument
        """
        resource_manager = visa.ResourceManager()
        self.visa_ref = resource_manager.open_resource(address)
        self.logger.info(
            'Instrument at {} connected successfully'.format(address))

    def command(self, command: str):
        """
        Sends a VISA command
        :param command: the SCPI command to send
        """
        self.visa_ref.clear()
        time.sleep(0.1)
        self.visa_ref.write(command)

    def read(self, query: str = 'READ?', parse: bool = True):
        """
        Sends a query request to the instrument

        :param query: the query command
        :param parse: whether to attempt to read the output as numbers
        :return: the readout from the instrument
        """
        self.visa_ref.clear()
        time.sleep(0.1)
        if parse:
            return self.visa_ref.query_ascii_values(query)
        else:
            return self.visa_ref.query(query)


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
        read = self.read(parse=False)
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
            self.command('UNIT:TEMP {}'.format(units))
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
        type_config = 'CONF:TEMP TC,T,(@{})'.format(str_channels)
        self.command(type_config)
        self.logger.info('Config written: {}'.format(type_config))

        read_config = 'SENS:TEMP:TRAN:TC:RJUN:TYPE FIX,(@{})'.format(
            str_channels)
        self.command(read_config)
        self.logger.info('Config written: {}'.format(read_config))

        valid_units = ['C', 'K', 'F']
        units = units.upper()
        if units in valid_units:
            unit_config = 'UNIT:TEMP {},(@{})'.format(units, str_channels)
            self.command(unit_config)
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
            data = self.read()
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

        :param channel: channel to set calibration for
        :param gain: multiplies the output
        :param offset: added to the output
        """
        self.cal_functions.update({channel: lambda x: gain*x + offset})

    def get_calibrated_temp(self, as_dict=False) -> Union[dict, list]:
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
        self.command('W GO 1')
        self.logger.info('Bath started')

    def stop(self):
        """Stops the bath"""
        self.command('W RR -1')
        self.logger.info('Bath stopped')

    def set_temp(self, temp: float):
        """Sets the temperature setpoint"""
        self.command('W SP {:.2f}'.format(temp))
        self.logger.info('Bath set to {}C'.format(temp))

    def get_temp(self) -> float:
        """Reads the current temperature"""
        read = self.read(query='R T1', parse=False)
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
        self.command('INTEG:RESET')
        self.logger.info('Integration reset')

    def start_integration(self):
        """Starts the power integration"""
        self.command('INTEG:START')
        self.logger.info('Integration started')

    def stop_integration(self):
        """Stops the power integration"""
        self.command('INTEG:STOP')
        self.logger.info('Integration stopped')

    def _read_sequence(self, value: str) -> float:
        self.measure_commands[1] = self.measure_commands[1].format(value)
        for command in self.measure_commands:
            self.command(command)
        return self.read(query='MEAS:NORM:VAL?')

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
        self.is_open = False
        self.logger = logging.getLogger('Solenoid @{}'.format(channel))
        self.logger.info('Initialized')

    def open(self):
        """Opens the solenoid"""
        self.parent.command('ROUT:OPEN (@{})'.format(self.channel))
        self.is_open = True
        self.logger.info('Opened')

    def close(self):
        """Closes the solenoid"""
        self.parent.command('ROUT:CLOS (@{})'.format(self.channel))
        self.is_open = False
        self.logger.info('Closed')


class BelimoValve:
    """Flow control valve connected to the DAQ"""

    def __init__(self, parent: DAQ, channel: int, volt_const: float = 0):
        """
        Creates a solenoid object connected to a specific DAQ

        :param parent: DAQ object that this valve is connected to
        :param channel: DAQ channel the valve is connected to
        :param volt_const: flow rate * volt_const = voltage to send
        """
        self.parent = parent
        self.channel = channel
        self.logger = logging.getLogger('Belimo valve @{}'.format(channel))
        self.volt_const = volt_const
        self.is_reset = False
        self.logger.info('Initialized')

    def _write_volts(self, volts: float):
        if not (0 <= volts <= 10):
            self.logger.critical('Invalid voltage ({:.2f} V)'.format(volts))
            raise IOError('Invalid voltage sent to Belimo valve')
        self.parent.command(
            'SOURCE:VOLT {:2.3}, (@{})'.format(volts, self.channel))

    def reset(self):
        """Resets to valve to zero"""
        self._write_volts(0)
        self.logger.info('Resetting to zero and waiting 60 s')
        time.sleep(60)

    def set_flow(self, flow_rate: float):
        if not self.is_reset:
            self.reset()
        v_send = flow_rate * self.volt_const
        self._write_volts(v_send)
        self.logger.info("Sending {:.2f} V ({} x {})".format(v_send, flow_rate,
                                                             self.volt_const))


class MTScale:
    """Mettler Toledo 1000 lb scale"""

    def __init__(self, parent: DAQ, channel: int, gain: float = 100.5320481071,
                 offset: float = -3.284305861022):
        """
        Creates a scale object connected to a specific DAQ

        :param parent: DAQ object that this valve is connected to
        :param channel: DAQ channel the valve is connected to
        """
        self.parent = parent
        self.channel = channel
        self.gain = gain
        self.offset = offset
        self.logger = logging.getLogger('Scale @{}'.format(channel))
        self.logger.info('Initialized')

    def weigh(self) -> float:
        """Reads the current weight in pounds"""
        self.parent.command('CONF:VOLT:DC AUTO,MAX, (@{})'.format(self.channel))
        raw_out = self.parent.read()
        return raw_out * self.gain + self.offset


class HumiditySensor:
    """Relative humidity sensor"""

    def __init__(self, parent: DAQ, channel: int, gain: float = 6250,
                 offset: float = -25):
        """
        Creates an RH sensor object connected to a specific DAQ

        :param parent: DAQ object that this sensor is connected to
        :param channel: DAQ channel the sensor is connected to
        """
        self.parent = parent
        self.channel = channel
        self.gain = gain
        self.offset = offset
        self.logger = logging.getLogger('RH Sensor @{}'.format(channel))

    def rh(self) -> float:
        """Reads the current RH"""
        self.parent.command('CONF:CURR:DC (@{})'.format(self.channel))
        raw_out = self.parent.read()
        return raw_out * self.gain + self.offset


def is_number(s: str) -> bool:
    """
    Returns if a given string input is a number

    :param s: the input to test
    :return: if the input is a number
    """
    try:
        float(s)
        return True
    except ValueError:
        return False
