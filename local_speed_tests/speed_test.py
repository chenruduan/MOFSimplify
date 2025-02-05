#!/usr/bin/env python
# -*- coding: utf-8 -*-
import flask
import pandas as pd
import tensorflow.keras
import numpy as np
import time
from tensorflow.keras import backend as K
import json
import string
import os
import shutil
import subprocess
import molSimplify
import pickle
import molSimplify.Classes.mol3D as ms_mol3D
import molSimplify.Informatics.RACassemble as ms_RAC
import molSimplify.python_nn.tf_ANN as ms_ANN
import pathlib 
import sys
from molSimplify.Scripts.generator import startgen_pythonic
from molSimplify.Scripts.molSimplify_io import getlicores
from bokeh.plotting import figure
from bokeh.resources import CDN
from bokeh.models import ColumnDataSource, SingleIntervalTicker, LinearAxis
from bokeh.embed import file_html
from bokeh.models import Span
from bokeh.models import ColorBar, LinearColorMapper, LogColorMapper, HoverTool
from bokeh.models.markers import Circle
from bokeh.palettes import Inferno256#,RdBu11#,Viridis256
from flask import jsonify
from molSimplify.Informatics.MOF.MOF_descriptors import get_primitive, get_MOF_descriptors;

cmap_bokeh = Inferno256
# cmap_bokeh = RdBu11 # optional select other colormaps

app = flask.Flask(__name__)

MOFSIMPLIFY_PATH = '/Users/gianmarcoterrones/Research/mofSimplify'


def main():
    # Generates solvent stability prediction
    # To do this, need to generate RAC featurization and Zeo++ geometry information for the MOF
    # Then, apply Aditya's model to make prediction

    print('TIME CHECK 1')

    # To begin, always go to main directory
    os.chdir(MOFSIMPLIFY_PATH)

    # Grab data
    # mydata = json.loads(flask.request.get_data())

    os.chdir("temp_file_creation") # changing directory

    # Write the data back to a cif file
    # cif_file = open('temp_cif.cif', 'w')
    # cif_file.write(mydata)
    # cif_file.close()


    # delete the RACs folder, then remake it (to start fresh for this prediction)
    shutil.rmtree('RACs')
    os.mkdir('RACs')

    # doing the same with the Zeo++ folder
    shutil.rmtree('zeo++')
    os.mkdir('zeo++')

    os.chdir("RACs") # move to RACs folder

    print('TIME CHECK 2')
    import time # debugging
    timeStarted = time.time() # save start time (debugging)

    # Next, running MOF featurization
    try:
        get_primitive('../temp_cif.cif', 'temp_cif_primitive.cif');
    except ValueError:
        return 'FAILED'

    timeDelta = time.time() - timeStarted # get execution time
    print('Finished process in ' + str(timeDelta) + ' seconds')

    timeStarted = time.time() # save start time (debugging)

    try:
        full_names, full_descriptors = get_MOF_descriptors('temp_cif_primitive.cif',3,path= str(pathlib.Path().absolute()), xyzpath= 'temp_cif.xyz');
    except ValueError:
        return 'FAILED'
    except NotImplementedError:
        return 'FAILED'
    except AssertionError:
        return 'FAILED'

    if (len(full_names) <= 1) and (len(full_descriptors) <= 1): # this is a featurization check from MOF_descriptors.py
        return 'FAILED'

    timeDelta = time.time() - timeStarted # get execution time
    print('Finished process in ' + str(timeDelta) + ' seconds')

    print('TIME CHECK 3')

    # At this point, have the RAC featurization. Need geometry information next.

    # Run Zeo++
    os.chdir('..')
    os.chdir('zeo++')

    timeStarted = time.time() # save start time (debugging)

    cmd1 = '../../zeo++-0.3/network -ha -res temp_cif_pd.txt ' + '../RACs/temp_cif_primitive.cif'
    cmd2 = '../../zeo++-0.3/network -sa 1.86 1.86 10000 temp_cif_sa.txt ' + '../RACs/temp_cif_primitive.cif'
    cmd3 = '../../zeo++-0.3/network -ha -vol 1.86 1.86 10000 temp_cif_av.txt ' + '../RACs/temp_cif_primitive.cif'
    cmd4 = '../../zeo++-0.3/network -volpo 1.86 1.86 10000 temp_cif_pov.txt '+ '../RACs/temp_cif_primitive.cif'
    # four parallelized Zeo++ commands
    process1 = subprocess.Popen(cmd1, stdout=subprocess.PIPE, stderr=None, shell=True)
    process2 = subprocess.Popen(cmd2, stdout=subprocess.PIPE, stderr=None, shell=True)
    process3 = subprocess.Popen(cmd3, stdout=subprocess.PIPE, stderr=None, shell=True)
    process4 = subprocess.Popen(cmd4, stdout=subprocess.PIPE, stderr=None, shell=True)
    output1 = process1.communicate()[0]
    output2 = process2.communicate()[0]
    output3 = process3.communicate()[0]
    output4 = process4.communicate()[0]

    timeDelta = time.time() - timeStarted # get execution time
    print('Finished process in ' + str(timeDelta) + ' seconds')

    # Have written output of Zeo++ commands to files. Now, code below extracts information from those files

    ''' The geometric descriptors are largest included sphere (Di), 
    largest free sphere (Df), largest included sphere along free path (Dif),
    crystal density (rho), volumetric surface area (VSA), gravimetric surface (GSA), 
    volumetric pore volume (VPOV) and gravimetric pore volume (GPOV). 
    Also, we include cell volume as a descriptor.

    All Zeo++ calculations use a pore radius of 1.86 angstrom, and zeo++ is called by subprocess.
    '''

    timeStarted = time.time() # save start time (debugging)

    dict_list = []
    # base_dir = sys.argv[1] #base_dir must be an absolute path
    # if base_dir[-1] != '/':
    #     base_dir+='/'
    # for cif_file in os.listdir(base_dir+'/primitive/'):
    #     print('---- now on ----, '+cif_file)
    #     if '.cif' not in cif_file:
    #         continue
    #     basename = cif_file.strip('.cif')
    cif_file = 'temp.cif' # techincally, calculations were with the primitive, but I'll just call it temp
    basename = cif_file.strip('.cif')
    largest_included_sphere, largest_free_sphere, largest_included_sphere_along_free_sphere_path  = np.nan, np.nan, np.nan
    unit_cell_volume, crystal_density, VSA, GSA  = np.nan, np.nan, np.nan, np.nan
    VPOV, GPOV = np.nan, np.nan
    POAV, PONAV, GPOAV, GPONAV, POAV_volume_fraction, PONAV_volume_fraction = np.nan, np.nan, np.nan, np.nan, np.nan, np.nan
    if (os.path.exists('temp_cif_pd.txt') & os.path.exists('temp_cif_sa.txt') &
        os.path.exists('temp_cif_av.txt') & os.path.exists('temp_cif_pov.txt')
        ):
        with open('temp_cif_pd.txt') as f:
            pore_diameter_data = f.readlines()
            for row in pore_diameter_data:
                largest_included_sphere = float(row.split()[1]) # largest included sphere
                largest_free_sphere = float(row.split()[2]) # largest free sphere
                largest_included_sphere_along_free_sphere_path = float(row.split()[3]) # largest included sphere along free sphere path
        with open('temp_cif_sa.txt') as f:
            surface_area_data = f.readlines()
            for i, row in enumerate(surface_area_data):
                if i == 0:
                    unit_cell_volume = float(row.split('Unitcell_volume:')[1].split()[0]) # unit cell volume
                    crystal_density = float(row.split('Unitcell_volume:')[1].split()[0]) # crystal density
                    VSA = float(row.split('ASA_m^2/cm^3:')[1].split()[0]) # volumetric surface area
                    GSA = float(row.split('ASA_m^2/g:')[1].split()[0]) # gravimetric surface area
        with open('temp_cif_pov.txt') as f:
            pore_volume_data = f.readlines()
            for i, row in enumerate(pore_volume_data):
                if i == 0:
                    density = float(row.split('Density:')[1].split()[0])
                    POAV = float(row.split('POAV_A^3:')[1].split()[0]) # Probe accessible pore volume
                    PONAV = float(row.split('PONAV_A^3:')[1].split()[0]) # Probe non-accessible probe volume
                    GPOAV = float(row.split('POAV_cm^3/g:')[1].split()[0])
                    GPONAV = float(row.split('PONAV_cm^3/g:')[1].split()[0])
                    POAV_volume_fraction = float(row.split('POAV_Volume_fraction:')[1].split()[0]) # probe accessible volume fraction
                    PONAV_volume_fraction = float(row.split('PONAV_Volume_fraction:')[1].split()[0]) # probe non accessible volume fraction
                    VPOV = POAV_volume_fraction+PONAV_volume_fraction
                    GPOV = VPOV/density
    else:
        print('Not all 4 files exist, so at least one Zeo++ call failed!', 'sa: ',os.path.exists('temp_cif_sa.txt'), 
              '; pd: ',os.path.exists('temp_cif_pd.txt'), '; av: ', os.path.exists('temp_cif_av.txt'),
              '; pov: ', os.path.exists('temp_cif_pov.txt'))
        return 'FAILED'
    geo_dict = {'name':basename, 'cif_file':cif_file, 'Di':largest_included_sphere, 'Df': largest_free_sphere, 'Dif': largest_included_sphere_along_free_sphere_path,
                'rho': crystal_density, 'VSA':VSA, 'GSA': GSA, 'VPOV': VPOV, 'GPOV':GPOV, 'POAV_vol_frac':POAV_volume_fraction, 
                'PONAV_vol_frac':PONAV_volume_fraction, 'GPOAV':GPOAV,'GPONAV':GPONAV,'POAV':POAV,'PONAV':PONAV}
    dict_list.append(geo_dict)
    geo_df = pd.DataFrame(dict_list)
    geo_df.to_csv('geometric_parameters.csv',index=False)


    timeDelta = time.time() - timeStarted # get execution time
    print('Finished process in ' + str(timeDelta) + ' seconds')

    print('TIME CHECK 4')

    # Applying the model next

    # Merging geometric information with get_MOF_descriptors files (lc_descriptors.csv, sbu_descriptors.csv, linker_descriptors.csv)

    # from IPython.display import display # debugging

    lc_df = pd.read_csv("../../temp_file_creation/RACs/lc_descriptors.csv") 
    sbu_df = pd.read_csv("../../temp_file_creation/RACs/sbu_descriptors.csv")
    linker_df = pd.read_csv("../../temp_file_creation/RACs/linker_descriptors.csv")

    lc_df = lc_df.mean().to_frame().transpose() # averaging over all rows. Convert resulting Series into a Dataframe, then transpose
    sbu_df = sbu_df.mean().to_frame().transpose()
    linker_df = linker_df.mean().to_frame().transpose()

    # print('check U')
    # display(geo_df)
    # print(geo_df.columns)

    # print('check V')
    # display(lc_df) # debugging
    # print(lc_df.columns)

    merged_df = pd.concat([geo_df, lc_df, sbu_df, linker_df], axis=1)

    # print('check W')
    # display(merged_df) # debugging

    # merged_df = merged_df.merge(sbu_df, how='outer') 
    # merged_df = merged_df.merge(linker_df, how='outer') 

    # print('check X')
    # display(merged_df) # debugging

    merged_df.to_csv('../merged_descriptors.csv',index=False) # written in /temp_file_creation

    os.chdir('..')
    os.chdir('..')
    os.chdir('model/solvent/ANN')

    print('TIME CHECK 5')

    timeStarted = time.time() # save start time (debugging)

    os.system('python solvent_ANN.py > solvent_prediction.txt')
    # import for_GT
    # prediction = for_GT.main()

    timeDelta = time.time() - timeStarted # get execution time
    print('Finished process in ' + str(timeDelta) + ' seconds')

    f = open("solvent_prediction.txt", "r")
    line = f.read()
    line = line.split('[')
    line = line[2]
    line = line.split(']')
    prediction = line[0] # isolating just the prediction, since the model spits out the prediction like [[PREDICTION]], as in, in hard brackets
    f.close()

    print('TIME CHECK 6')

    return prediction

    # os.chdir('..')
    # os.chdir('..')
    # os.chdir('model/thermal/ANN')

    # print('TIME CHECK 5')

    # timeStarted = time.time() # save start time (debugging)

    # os.system('python thermal_ANN.py > thermal_prediction.txt')

    # timeDelta = time.time() - timeStarted # get execution time
    # print('Finished process in ' + str(timeDelta) + ' seconds')

    # f = open("thermal_prediction.txt", "r")
    # prediction = f.read()
    # f.close()

    # print('TIME CHECK 6')

    # return prediction

if __name__ == '__main__':
	main()