import argparse
import logging
import os
import sys

from tc_tools.instruments import PRT, DAQ, TCBath
from tc_tools.procedures import setpoint_calibration
from tc_tools.config import tc_calibration_config

parser = argparse.ArgumentParser()
parser.add_argument('-daq', '--daq_address', type=str, dest='daq',
                    default='GPIB0::9::INSTR', help='VISA address of the DAQ')
parser.add_argument('-prt', '--prt_address', type=str, dest='prt',
                    default='ASRL1::INSTR', help='VISA address of the PRT')
parser.add_argument('-bath', '--bath_address', type=str, dest='bath',
                    default='COM4', help='VISA address of the bath')
parser.add_argument('-o', '--output_file', type=str, dest='o',
                    help='Output file name or path', default='data.csv')
parser.add_argument('-s', '--set_points', nargs='+', dest='s',
                    help='Set points',
                    default=[5, 15, 25, 35, 45, 55, 65, 75])
parser.add_argument('-c', '--channels', nargs='+', dest='c', help='Channels')
parser.add_argument('-hd', '--headers', nargs='+', dest='hd',
                    help='Headers for the output file in the same order as the'
                         ' channel inputs')
parser.add_argument('-cfg', '--config_file', dest='cfg', type=str,
                    help='Name or path of configuration file.')
in_args = parser.parse_args()
cfg = tc_calibration_config(in_args.cfg)

name, _ = os.path.splitext(cfg['Files']['output file'])
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
    out_path = os.path.abspath(cfg['Files']['output file'])
except:
    sys.exit('Invalid output file name or path')

try:
    prt = PRT(cfg['Instruments']['PRT address'])
    logging.info('PRT initialized')
except Exception as e:
    logging.critical('PRT initialization error: ' + str(e))

try:
    daq = DAQ(cfg['Instruments']['DAQ address'])
    logging.info('DAQ initialized')
except Exception as e:
    logging.critical('DAQ initialization error: ' + str(e))

try:
    bath = TCBath(cfg['Instruments']['bath address'])
    logging.info('Bath initialized')
except Exception as e:
    logging.critical('Bath initialization error: ' + str(e))

channels = list(cfg['Procedure']['channels'].split())
set_points = list(cfg['Procedure']['set points'].split())

if cfg['Files']['headers'] == 'channels':
    headers = channels
else:
    headers = list(cfg['Files']['headers'].split())

if len(channels) != len(headers):
    sys.exit('Must have the same number of channels and headers. No spaces '
             'in names of headers')

try:
    setpoint_calibration(prt, daq, bath, set_points,
                         out_path, headers, channels)
    logging.info('Calibration successful')
except Exception as e:
    logging.critical('Exception during execution: {}'.format(type(e).__name__))

