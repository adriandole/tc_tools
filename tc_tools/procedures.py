from tc_tools.utils import *


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


def predraw(draws: int, draw_solenoid: Solenoid, power_meter: PowerMeter,
            daq: DAQ, tank_tc: List[int]):
    """
    Performs a number of predraws

    :param draws: number of draws
    :param draw_solenoid: solenoid object controlling the draws
    :param power_meter: power meter object
    :param daq: DAQ object
    :param tank_tc: channels of the tank thermocouples
    """
    if draws == 0:
        return

    daq.set_channels(tank_tc)
    for n in range(draws):
        draw_solenoid.open()
        power = power_meter.read_watts()
        while power < 100:
            time.sleep(3)
            power = power_meter.read_watts()
        draw_solenoid.close()
        while power > 100:
            time.sleep(3)
            power = power_meter.read_watts()
        t_delta = 1.0
        while t_delta > 0.1:
            temps = np.array(daq.get_calibrated_temp())
            max_temp = np.max(temps)
            avg = np.average(temps)
            t_delta = abs(max_temp - avg)
            time.sleep(60)
    time.sleep(3600)

def purge_loop(draw_solenoid: Solenoid):
    """
    Purges the loop of ambient-temp water

    :param draw_solenoid: solenoid controlling the loop
    """
    draw_solenoid.open()
    time.sleep(20)
    draw_solenoid.close()
    time.sleep(40)


def draw(flow_rate: float, draw_amount: float, draw_solenoid: Solenoid,
         weigh_solenoid: Solenoid, scale: MTScale,
         flow_valve: BelimoValve, draw_writer: DrawWriter):
    """

    :param flow_rate: rate (gallons per minute) to send to the valve
    :param draw_solenoid: solenoid controlling the draw valve
    :param weigh_solenoid: solenoid controlling the weigh tank valve
    :param flow_valve: Belimo variable flow valve
    :param draw_writer: writer object for draw data
    """
    purge_loop(draw_solenoid)
    flow_valve.reset()
    weigh_solenoid.close()
    draw_writer.read_data(initial=True)
    draw_solenoid.open()
    weight = 0.0
    draw_writer.reset()
    while weight < 8.217 * draw_amount:
        draw_writer.read_data()
        weight = scale.weigh()
        time.sleep(2)