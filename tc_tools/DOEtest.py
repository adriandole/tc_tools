import argparse
import logging
import os
import sys
import time
from multiprocessing import Process

import tc_tools.instruments as i
import tc_tools.procedures as p
import tc_tools.utils as u

data_headers = ['Elapsed', 'Draw Status', 'Inst. Tank Avg', 'Tank 1',
                'Tank 2', 'Tank 3', 'Tank 4', 'Tank 5', 'Tank 6',
                'Inlet', 'Outlet', 'Ambient', 'RH', 'Power',
                'Energy']

draw_headers = ['Elapsed', 'Inlet Temperature', 'Outlet Temperature',
                'Scale Weight']

parser = argparse.ArgumentParser()
parser.add_argument('-daq', '--daq_address', type=str, dest='daq',
                    default='GPIB0::9::INSTR', help='VISA address of the DAQ')
parser.add_argument('-pmr', '--power_meter_address', type=str, dest='pmr',
                    default='ASRL1::INSTR', help='VISA address of the PRT')
parser.add_argument('-o', '--output_file', type=str, dest='o',
                    help='Output file name or path', default='data.csv')
parser.add_argument('-dr', '--draw_file', type=str, dest='dr',
                    help='Draw file name or path', default='draws.csv')
parser.add_argument('-sh', '--schedule_file', type=str, dest='sh',
                    help='Output file name or path', default='schedule.csv')
parser.add_argument('-tc', '--tank_channels', nargs='+', dest='tc',
                    help='Channels')
parser.add_argument('-ic', '--inlet_channel', type=int, dest='ic',
                    help='Tank inlet thermocouple channel')
parser.add_argument('-oc', '--outlet_channel', type=int, dest='oc',
                    help='Tank outlet thermocouple channel')
parser.add_argument('-sc', '--scale_channel', type=int, dest='sc',
                    help='Channel of the scale connected to the DAQ')
parser.add_argument('-ds', '--draw_solenoid', type=int, dest='ds',
                    help='Channel of the draw solenoid')
parser.add_argument('-ws', '--tank_channel', type=int, dest='ws',
                    help='Channel of the weigh tank solenoid')
parser.add_argument('-vc', '--valve_channel', type=int, dest='vc',
                    help='Channel of the Belimo flow valve')
parser.add_argument('-rhc', '--rh_channel', type=int, dest='rhc',
                    help='Channel of the RH sensor')
parser.add_argument('-dhd', '--draw_headers', nargs='+', dest='dhd',
                    help='Headers for the output file in the same order as the'
                         ' channel inputs', default=draw_headers)
parser.add_argument('-ohd', '--out_headers', nargs='+', dest='ohd',
                    help='Headers for the output file in the same order as the'
                         ' channel inputs', default=data_headers)
in_args = parser.parse_args()
name, _ = os.path.splitext(in_args.o)

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %('
                           'message)s',
                    datefmt='%m-%d %H:%M',
                    filename=name + '.log',
                    filemode='w')
console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)

try:
    schedule_file = os.path.abspath(in_args.sc)
    output_file = os.path.abspath(in_args.o)
    draw_file = os.path.abspath(in_args.dr)
    logging.info('Files initialized')
except Exception as e:
    print(str(e))
    sys.exit('Invalid file name or path')

try:
    daq = i.DAQ(in_args.daq)
    pmr = i.PowerMeter(in_args.pmr)
except Exception as e:
    print(str(e))
    sys.exit('Error initializing instruments')

try:
    draw_solenoid = i.Solenoid(daq, in_args.ds)
    weigh_solenoid = i.Solenoid(daq, in_args.ws)
    flow_valve = i.BelimoValve(daq, in_args.vc)
    scale = i.MTScale(daq, in_args.sc)
    rh_sensor = i.HumiditySensor(daq, in_args.rhc)
except Exception as e:
    print(str(e))
    sys.exit('Error initializing channel instruments')

try:
    draw_writer = u.DrawWriter(in_args.dhd, output_file, in_args.ic, in_args.oc,
                               daq, scale)
    min_writer = u.SimulatedUseWriter(in_args.ohd, draw_file, daq, rh_sensor,
                                      pmr)
except Exception as e:
    print(str(e))
    sys.exit('Error initializing writers')

schedule = p.parse_schedule(schedule_file)
start_time = time.time()
elapsed = 0.0
draw_num = 1
draws_finished = False
while elapsed < (schedule.time[-1] + 60):
    min_writer.read_data()
    elapsed = time.time() - start_time
    if (elapsed >= schedule.time[draw_num]) and not draws_finished:
        draw_process = Process(target=p.draw,
                               args=(schedule.rate[draw_num],
                                     schedule.volume[draw_num], draw_solenoid,
                                     weigh_solenoid, scale, flow_valve,
                                     draw_writer))
        draw_process.start()
    if draw_num == (len(schedule.time) - 1):
        draws_finished = True
    else:
        draw_num += 1
    time.sleep(60.0 - ((time.time() - start_time) % 60.0))

