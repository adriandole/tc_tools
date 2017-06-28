import argparse
from tc_tools.procedures import setpoint_calibration

parser = argparse.ArgumentParser()
parser.add_argument('-daq', '--daq_address', type=str, dest='daq',
                    default='GPIB0::9::INSTR', help='VISA address of the DAQ')
parser.add_argument('-prt', '--prt_address', type=str, dest='prt',
                    default='ASRL1::INSTR', help='VISA address of the PRT')
parser.add_argument('-bath', '--bath_address', type=str, dest='bath',
                    default='COM4', help='VISA address of the bath')
parser.add_argument('-o', '--output_file', type=str, dest='o',
                    help='Output file name or path', default='data.csv')
parser.add_argument('-s', '--set_points', nargs='+', dest='s', help='Set points',
                    default=[5, 15, 25, 35, 45, 55, 65, 75])
parser.add_argument('-c', '--channels', nargs='+', dest='c', help='Channels')
parser.add_argument('-hd', '--headers', nargs='+', dest='hd',
                    help='Headers for the output file in the same order as the'
                         ' channel inputs')
in_args = parser.parse_args()

try:
    setpoint_calibration(in_args.prt, in_args.daq, in_args.bath, in_args.s,
                         in_args.o, in_args.hd, in_args.c)
except Exception as e:
    print(e)
