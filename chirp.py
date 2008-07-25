#!/usr/bin/python
#
# Copyright 2008 Dan Smith <dsmith@danplanet.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import serial
import sys
from optparse import OptionParser

from chirp import ic9x, id800, ic2820, ic2200, chirp_common, errors

def fail_unsupported():
    print "Operation not supported by selected radio"
    sys.exit(1)

def fail_missing_mmap():
    print "mmap-only operation requires specification of an mmap file"
    sys.exit(1)

RADIOS = { "ic9x:A": ic9x.IC9xRadioA,
           "ic9x:B": ic9x.IC9xRadioB,
           "id800" : id800.ID800v2Radio,
           "ic2820": ic2820.IC2820Radio,
           "ic2200": ic2200.IC2200Radio,
}

parser = OptionParser()
parser.add_option("-s", "--serial", dest="serial",
                  default="mmap",
                  help="Serial port (default: mmap)")
parser.add_option("-i", "--id", dest="id",
                  default=False,
                  action="store_true",
                  help="Request radio ID string")
parser.add_option("", "--get-mem", dest="get_mem",
                  default=False,
                  action="store_true",
                  help="Get and print memory location")
parser.add_option("", "--set-mem-name", dest="set_mem_name",
                  default=None,
                  help="Set memory name")
parser.add_option("", "--set-mem-freq", dest="set_mem_freq",
                  type="float",
                  default=None,
                  help="Set memory frequency")
parser.add_option("", "--set-mem-toneon", dest="set_mem_toneon",
                  default=False,
                  action="store_true",
                  help="Set tone enabled flag")
parser.add_option("", "--set-mem-toneoff", dest="set_mem_toneoff",
                  default=False,
                  action="store_true",
                  help="Set tone disabled flag")
parser.add_option("", "--set-mem-tone", dest="set_mem_tone",
                  type="float",
                  help="Set memory tone")
parser.add_option("", "--set-mem-dup", dest="set_mem_dup",
                  help="Set memory duplex (+,-, or blank)")
parser.add_option("", "--set-mem-mode", dest="set_mem_mode",
                  default=None,
                  help="Set mode (%s)" % ",".join(chirp_common.MODES))
parser.add_option("-r", "--radio", dest="radio",
                  default=None,
                  help="Radio model (one of %s)" % ",".join(RADIOS.keys()))

parser.add_option("", "--mmap", dest="mmap",
                  default=None,
                  help="Radio memory map file location")
parser.add_option("", "--download-mmap", dest="download_mmap",
                  action="store_true",
                  default=False,
                  help="Download memory map from radio")
parser.add_option("", "--upload-mmap", dest="upload_mmap",
                  action="store_true",
                  default=False,
                  help="Upload memory map to radio")

(options, args) = parser.parse_args()

if options.id:
    from chirp import icf
    from chirp import util

    s = serial.Serial(port=options.serial,
                      baudrate=9600,
                      timeout=0.5)

    md = icf.get_model_data(s)

    print "Model:\n%s" % util.hexprint(md)

    sys.exit(0)

if not options.radio:
    print "Must specify a radio model"
    sys.exit(1)
else:
    rclass = RADIOS[options.radio]

if options.serial == "mmap":
    if options.mmap:
        s = options.mmap
    else:
        s = options.radio + ".img"
else:
    s = serial.Serial(port=options.serial,
                      baudrate=rclass.BAUD_RATE,
                      timeout=0.5)

radio = rclass(s)

if options.set_mem_tone:
    try:
        chirp_common.TONES.index(options.set_mem_tone)
    except:
        print "Invalid tone `%s'" % options.set_mem_tone
        print "Valid tones:\n%s" % chirp_common.TONES
        sys.exit(1)

    _tone = options.set_mem_tone
else:
    _tone = None

if options.set_mem_dup is not None:
    if options.set_mem_dup != "+" and \
            options.set_mem_dup != "-" and \
            options.set_mem_dup != "":
        print "Invalid duplex value `%s'" % options.set_mem_dup
        print "Valid values are: '+', '-', ''"
        sys.exit(1)
    else:
        _dup = options.set_mem_dup
else:
    _dup = None

if options.set_mem_mode:
    print "Set mode: %s" % options.set_mem_mode
    if options.set_mem_mode not in chirp_common.MODES:
        print "Invalid mode `%s'"
        sys.exit(1)
    else:
        _mode = options.set_mem_mode
else:
    _mode = None

if options.set_mem_name or options.set_mem_freq or \
        options.set_mem_toneon or options.set_mem_toneoff or \
        options.set_mem_tone or options.set_mem_dup is not None or \
        options.set_mem_mode:
    try:
        mem = radio.get_memory(int(args[0]))
    except errors.InvalidMemoryLocation:
        mem = chirp_common.Memory()
        mem.number = int(args[0])

    mem.name   = options.set_mem_name or mem.name
    mem.freq   = options.set_mem_freq or mem.freq
    mem.tone   = _tone or mem.tone
    if _dup is not None:
        mem.duplex = _dup
    mem.mode   = _mode or mem.mode

    if options.set_mem_toneon:
        mem.toneEnabled = True
    elif options.set_mem_toneoff:
        mem.toneEnabled = False

    radio.set_memory(mem)

if options.get_mem:
    try:
        mem = radio.get_memory(int(args[0]))
    except errors.InvalidMemoryLocation:
        mem = chirp_common.Memory()
        mem.number = int(args[0])
        
    print mem

if options.download_mmap:
    isinstance(radio, chirp_common.IcomMmapRadio) or fail_unsupported()
    radio.sync_in()
    radio.save_mmap(options.mmap)

if options.upload_mmap:
    isinstance(radio, chirp_common.IcomMmapRadio) or fail_unsupported()
    radio.load_mmap(options.mmap)
    if radio.sync_out():
        print "Clone successful"
    else:
        print "Clone failed"

if options.mmap and isinstance(radio, chirp_common.IcomMmapRadio):
    radio.save_mmap(options.mmap)
    
