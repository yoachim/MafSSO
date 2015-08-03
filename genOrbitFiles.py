#! /usr/bin/env python
import numpy as np
import matplotlib.pyplot as plt
from moObs import MoObs, runMoObs
from lsst.sims.maf.db import OpsimDatabase
import os, argparse

# Gererate the orbit files for each opsim run

#runNames = ['ops2_1094', 'enigma_1257',
#            'enigma_1258','enigma_1259','enigma_1189']

def runThem(runName,useCamera=True):


    orbitfile = 'pha20141031.des'

    dbcols = ['expMJD', 'night', 'fieldRA', 'fieldDec', 'rotSkyPos', 'filter',
              'finSeeing', 'fiveSigmaDepth', 'visitExpTime', 'solarElong']

    print 'Generating orbit file for %s' % runName
    extraS = ''
    if not useCamera:
        extraS = '_NoCam'

    outfilename = runName+extraS+'_out.txt'
    runMoObs(orbitfile, outfilename,
             '/Users/yoachim/Scratch/Opsim_sqlites/'+runName+'_sqlite.db',
             dbcols=dbcols, useCamera=useCamera)
if __name__=="__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('runName', type=str, default=None)
    parser.add_argument('--camera', dest="camera", action='store_true', default=False)
    args, extras = parser.parse_known_args()

    runThem(args.runName, useCamera=args.camera)


    # To run in parallel:
    # cat runList.txt | xargs -P 3 -I CMD bash -c './genOrbitFiles.py CMD --camera'
