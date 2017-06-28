from tc_tools.instruments import PRT, DAQ, TCBath
from tc_tools.utils import TempWriter, steady_state_monitor
import time


def setpoint_calibration(prt_address, daq_address, bath_address, set_points,
                         output_file, headers, channels):
    writer = TempWriter(output_file, headers)

    prt = PRT(prt_address)
    daq = DAQ(daq_address)
    daq.set_channels(channels)
    bath = TCBath(bath_address)
    
    bath.start()
    print('Bath started')

    for point in set_points:
        bath.set_temp(point)
        print('Proceeding to point: {}C'.format(point))
        if steady_state_monitor(prt):
            writer.collect_data(prt, daq)

    bath.stop()
