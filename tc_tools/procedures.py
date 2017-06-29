import logging
from tc_tools.instruments import PRT, DAQ, TCBath
from tc_tools.utils import TempWriter, steady_state_monitor


def setpoint_calibration(prt_address, daq_address, bath_address, set_points,
                         output_file, headers, channels):
    """
    Runs the calibration procedure

    :param prt_address: VISA address of the PRT
    :type prt_address: str
    :param daq_address: VISA address of the DAQ
    :type daq_address: str
    :param bath_address: VISA address of the bath
    :type bath_address: str
    :param set_points: list of temperature set points
    :type set_points: list
    :param output_file: path to output file
    :type output_file: os.path.abspath
    :param headers: headers for the output file
    :type headers: list
    :param channels: channels to collect data from
    :type channels: list
    """
    logging.info('Calibration procedure started')
    logger = logging.getLogger('Calibration')

    try:
        prt = PRT(prt_address)
        logger.info('PRT initialized')
    except Exception as e:
        logger.critical('PRT initialization error: ' + str(e))

    try:
        daq = DAQ(daq_address)
        logger.info('DAQ initialized')
    except Exception as e:
        logger.critical('DAQ initialization error: ' + str(e))

    try:
        bath = TCBath(bath_address)
        logger.info('Bath initialized')
    except Exception as e:
        logger.critical('Bath initialization error: ' + str(e))

    writer = TempWriter(output_file, headers)

    daq.set_channels(channels)
    if max(daq.get_temp()) - prt.get_temp() < 1:
        logger.info('DAQ and PRT readings within 1°')
    else:
        logger.warning('DAQ and PRT differ by more than 1°. Possible setup issues')

    bath.start()

    for point in set_points:
        bath.set_temp(point)
        logger.info('Proceeding to point: {}C'.format(point))
        if steady_state_monitor(prt):
            logger.info('Steady state achieved')
            writer.collect_data(prt, daq)

    bath.stop()
