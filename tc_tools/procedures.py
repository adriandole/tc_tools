import logging
import os
from tc_tools.instruments import *
from tc_tools.utils import CalibrationWriter, steady_state_monitor


def setpoint_calibration(prt: PRT, daq: DAQ, bath: TCBath, set_points: list,
                         output_file: os.path.abspath, headers: list,
                         channels: list):
    """
    Runs the calibration procedure

    :param prt: PRT object to use
    :param daq: DAQ object to use
    :param bath: TCBath object to use
    :param set_points: list of temperature set points
    :param output_file: path to output file
    :param headers: headers for the output file
    :param channels: channels to collect data from
    """
    logging.info('Calibration procedure started')
    logger = logging.getLogger('Calibration')

    writer = CalibrationWriter(output_file, headers)

    daq.set_channels(channels)
    if max(daq.get_temp_uncalibrated()) - prt.get_temp() < 1:
        logger.info('DAQ and PRT readings within 1°')
    else:
        logger.warning(
            'DAQ and PRT differ by more than 1°. Possible setup issues')

    bath.start()

    for point in set_points:
        bath.set_temp(point)
        logger.info('Proceeding to point: {}C'.format(point))
        if steady_state_monitor(prt):
            logger.info('Steady state achieved')
            writer.collect_data(prt, daq)

    bath.stop()

def predraw(draws: int, draw_solenoid: Solenoid, power_meter: PowerMeter):
    if draws == 0:
        return
    for n in range(draws):
        draw_solenoid.open()