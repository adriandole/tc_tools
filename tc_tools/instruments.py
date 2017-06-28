import visa
import time
import sys
import warnings
from tc_tools.utils import is_number


class VISAInstrument:
    """Wrapper for PyVisa instruments"""

    def __init__(self, address):
        """
        Gets a VISA instrument from a resource manager

        :param address: VISA address of the instrument
        :type address: str
        """
        resource_manager = visa.ResourceManager()
        self._visa_ref = resource_manager.open_resource(address)


class PRT(VISAInstrument):
    """Hart Scientific PRT"""
    def __init__(self, address):
        """
        Calls the super constructor and sets the units to C

        :param address: VISA address of the instrument
        :type address: str
        """
        super(PRT, self).__init__(address)
        self.set_units('C')

    def get_temp(self):
        """
        Reads the temperature

        :return: the temperature reading
        :rtype: float
        """
        time.sleep(1)
        self._visa_ref.clear()
        time.sleep(1)
        read = self._visa_ref.query('READ?')
        # Portion of the output with temperature digits
        temp_portion = read[5:11]
        if not (is_number(temp_portion) and (float(temp_portion) > 0)):
            print('PRT read error. Retrying')
            raise IOError
        return float(temp_portion)

    def set_units(self, units):
        """
        Changes the output units

        :param units: temperature units; C, K, or F
        :type units: str
        """
        valid_units = ['C', 'K', 'F']
        units = units.upper()
        if units in valid_units:
            # Sleep before writing prevents quick sequential writes, which may cause errors
            time.sleep(1)
            self._visa_ref.write('UNIT:TEMP {}'.format(units))


class DAQ(VISAInstrument):
    """Agilent 34970A"""
    channels_set = False

    def set_channels(self, channels):
        """
        Sets the channels to read from

        :param channels: channels to read as a list
        :type channels: list
        """
        str_channels = ','.join(channels)
        time.sleep(1)
        self._visa_ref.write('CONF:TEMP TC,T,(@{})'.format(str_channels))
        time.sleep(1)
        self._visa_ref.write('SENS:TEMP:TRAN:TC:RJUN:TYPE FIX,(@{})'.format(str_channels))
        self.channels_set = True

    def get_temp(self):
        """
        Reads the set channels

        :return: temperature readings, ordered by channel
        :rtype: list
        """
        if self.channels_set:
            self._visa_ref.clear()
            time.sleep(1)
            data = self._visa_ref.query_ascii_values('READ?')
            if not all(n > 0 for n in data):
                raise IOError
            return data
        else:
            raise UserWarning('Set DAQ channels before reading data')



class TCBath(VISAInstrument):
    """Thermo AC25 bath"""
    def start(self):
        """Starts the bath"""
        time.sleep(1)
        self._visa_ref.write('W GO 1')

    def stop(self):
        """Stops the bath"""
        time.sleep(1)
        self._visa_ref.write('W RR -1')

    def set_temp(self, temp):
        """
        Sets the temperature setpoint

        :param temp: temperature to set to
        :type temp: float
        """
        time.sleep(1)
        self._visa_ref.write('W SP {:.2f}'.format(temp))

    def get_temp(self):
        """
        Reads the current temperature

        :return: temperature reading
        :rtype: float
        """
        time.sleep(1)
        read = self._visa_ref.query('R T1')
        try:
            if len(read) > 5:
                temp_portion = read[3:-4]
            if is_number(temp_portion):
                return float(temp_portion)
        except:
            print('Read error')
