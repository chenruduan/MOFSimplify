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
# app.config['SECRET_KEY'] = "secretkeythatisverysecret,averysecretsecretkey"
# next, session code added by Gianmarco
# SESSION_TYPE = 'redis'
# app.config.from_object(__name__)
#sess = Session(app)

# # Display text for neural network predictions
# results_string='''<b>Results</b>
# <br> ΔE<sub>H-L</sub> = %.1f kcal/mol predicted for the provided structure.
# <br> This corresponds to S=%s being the ground state.
# <br>
# <br> <b>Value</b>
# <br> When |ΔE<sub>H-L</sub>| < 5 kcal/mol, the complex is a potential spin-crossover complex (SCO), which can have important implications in catalytic reaction cycles.
# <br> Our machine learning (ML) models [<a href="https://doi.org/10.1039/C7SC01247K">1</a>] took %.3f seconds to predict the geometry, spin splitting energy, and more for this complex!
# <br> By comparison, density functional theory (DFT) optimizations on the two structures to get these properties would take about an hour using one Nvidia 970 GPU.
# <br> molSimplify can help accelerate discovery of new materials, such as SCOs! [<a href="https://doi.org/10.1021/acs.jpclett.8b00170">2</a>]
# <br>
# <br> <b>Details</b>
# <br> The ML models are trained on data from density functional theory (DFT) with the B3LYP functional, the LANL2DZ effective core potential for metal atoms, and the 6-31G* basis set for all other atoms.
# <br> Warning: the training data do not include 4d transition metals, so results for these are extrapolations and may not be as accurate.
# '''

# licores = getlicores()

# # Pre-load neural networks to save time later
# valid_predictors = ['ls_ii', 'split']
# predictor_vars = {}
# # Load time is 0.5 seconds per predictor (only happens once, when server is started)
# for predictor_name in valid_predictors:
#     curr_dict = {}
#     curr_dict['train_vars'] = ms_ANN.load_ANN_variables(predictor_name)
#     curr_dict['norm_data'] = ms_ANN.load_normalization_data(predictor_name)
#     curr_dict['my_ANN'] = ms_ANN.load_keras_ann(predictor_name)
#     curr_dict['my_ANN']._make_predict_function()
#     curr_dict['train_x'] = ms_ANN.load_training_data(predictor_name)
#     predictor_vars[predictor_name] = curr_dict

# # Pre-load PCA for plotting
# pca_plot_df = pd.read_csv('data/pca_for_bokeh.csv')
# with open('data/rac_names.txt','r') as file1:
#     lines = file1.readlines()
# pca_variables = [x.strip('\n') for x in lines]
# # pca_model = pickle.load(open('data/PCA_model.pkl','rb')) # removed
# with open('data/PCA_model.pkl','rb') as f: # next 4 lines were added by Gianmarco Terrones, for Python 3
#     u = pickle._Unpickler(f)
#     u.encoding = 'latin1'
#     pca_model = u.load()

# # KDE data for plotting
# datadf = pd.read_csv('data/kde_data.csv')

# def perform_ANN_prediction(RAC_dataframe, predictor_name, RAC_column='RACs'):
#     # Function that performs ANN predictions (written quite inefficiently)
#     assert type(RAC_dataframe) == pd.DataFrame
#     start_time = time.time()

#     curr_dict = predictor_vars[predictor_name]
#     train_vars = curr_dict['train_vars']
#     train_mean_x, train_mean_y, train_var_x, train_var_y = curr_dict['norm_data']
#     my_ANN = curr_dict['my_ANN']
#     train_x = curr_dict['train_x']
#     #train_vars = load_ANN_variables(predictor_name)
#     #train_mean_x, train_mean_y, train_var_x, train_var_y = load_normalization_data(predictor_name)
#     #my_ANN = load_keras_ann(predictor_name)

#     # Check if any RAC elements are missing from the provided dataframe
#     missing_labels = [i for i in train_vars if i not in RAC_dataframe.columns]

#     if len(missing_labels) > 0:
#         # Try checking if there is anything in the column `RAC_column`. If so, deserialize it and re-run.
#         if RAC_column in RAC_dataframe.columns:
#             deserialized_RACs = pd.DataFrame.from_records(RAC_dataframe[RAC_column].values, index=RAC_dataframe.index)
#             deserialized_RACs = deserialized_RACs.astype(float)
#             RAC_dataframe = RAC_dataframe.join(deserialized_RACs)
#             return perform_ANN_prediction(RAC_dataframe, predictor_name, RAC_column='RACs')
#         else:
#             raise ValueError('Please supply missing variables in your RAC dataframe: %s' % missing_labels)
#     if 'alpha' in train_vars:
#         if any(RAC_dataframe.alpha > 1):
#             raise ValueError('Alpha is too large - should be between 0 and 1.')
#     RAC_subset_for_ANN = RAC_dataframe.loc[:,train_vars].astype(float)
#     normalized_input = ms_ANN.data_normalize(RAC_subset_for_ANN, train_mean_x, train_var_x)
#     ANN_prediction = my_ANN.predict(normalized_input)
#     rescaled_output = ms_ANN.data_rescale(ANN_prediction, train_mean_y, train_var_y)
#     # Get latent vectors for training data and queried data
#     #train_x = load_training_data(predictor_name)
#     #train_x = pd.DataFrame(train_x, columns=train_vars).astype(float)
#     #get_outputs = K.function([my_ANN.layers[0].input, K.learning_phase()],
#     #                         [my_ANN.layers[len(my_ANN.layers) - 2].output])
#     #normalized_train = ms_ANN.data_normalize(train_x, train_mean_x, train_var_x)
#     #training_latent = get_outputs([normalized_train, 0])[0]
#     #query_latent = get_outputs([normalized_input, 0])[0]


#     # Append all results to dataframe
#     results_allocation = [None for i in range(len(RAC_dataframe))]
#     for i in range(len(RAC_dataframe)):
#         results_dict = {}
#         #min_latent_distance = min(np.linalg.norm(training_latent - query_latent[i][:], axis=1))
#         #results_dict['%s_latent_vector' % predictor_name] = query_latent[i]
#         #results_dict['%s_min_latent_distance' % predictor_name] = min_latent_distance
#         output_value = rescaled_output[i]
#         if len(output_value) == 1: # squash array of length 1 to the value it contains
#             output_value = output_value[0]
#         results_dict['%s_prediction' % predictor_name] = output_value
#         results_allocation[i] = results_dict
#     results_df = pd.DataFrame(results_allocation, index=RAC_dataframe.index)
#     RAC_dataframe_with_results = RAC_dataframe.join(results_df)
#     return RAC_dataframe_with_results

@app.route('/demo')
def serve_demo():
    # Go to localhost:8000/demo to see this.
    return 'you are on the demo page'

@app.route('/logo.png')
def serve_logo():
    return flask.send_from_directory('.', 'logo.png')

@app.route('/truncated_logo.png')
def serve_truncated_logo():
    return flask.send_from_directory('.', 'truncated_logo.png')

@app.route('/')
def serve_homepage():
    # Serves homepage
    return flask.send_from_directory('.', 'index.html')

@app.route('/about.html')
def serve_about():
    # Serves homepage
    return flask.send_from_directory('.', 'about.html')

@app.route('/ris_files/<path:path>')
def serve_ris(path):
    # Serves homepage
    return flask.send_from_directory('ris_files', path)

@app.route('/how_to_cite.html')
def serve_cite():
    # Serves homepage
    return flask.send_from_directory('.', 'how_to_cite.html')

@app.route('/libraries/<path:path>')
def serve_library_files(path):
    # Serves libraries
    return flask.send_from_directory('libraries', path)
    
# Note: the h5 model for the solvent stability prediction and the thermal stability prediction should be trained on the same version of Terachem (here, 1.14)
# the two h5 models show up in solvent_ANN.py and thermal_ANN.py, respectively
@app.route('/predict_solvent_stability', methods=['POST']) # Gianmarco Terrones addition
def ss_predict():
    # Generates solvent stability prediction
    # To do this, need to generate RAC featurization and Zeo++ geometry information for the MOF
    # Then, apply Aditya's model to make prediction

    print('TIME CHECK 1')

    # To begin, always go to main directory (this directory will vary depending on computer)
    os.chdir("/Users/gianmarcoterrones/Research/mofSimplify/")

    # Grab data
    mydata = json.loads(flask.request.get_data())

    os.chdir("temp_file_creation") # changing directory

    # Write the data back to a cif file
    cif_file = open('temp_cif.cif', 'w')
    cif_file.write(mydata)
    cif_file.close()


    # delete the RACs folder, then remake it (to start fresh for this prediction)
    shutil.rmtree('RACs')
    os.mkdir('RACs')

    # doing the same with the Zeo++ folder
    shutil.rmtree('zeo++')
    os.mkdir('zeo++')

    os.chdir("RACs") # move to RACs folder

    print('TIME CHECK 2')

    # Next, running MOF featurization
    try:
        get_primitive('../temp_cif.cif', 'temp_cif_primitive.cif');
    except ValueError:
        return 'FAILED'

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

    print('TIME CHECK 3')

    # At this point, have the RAC featurization. Need geometry information next.

    # Run Zeo++
    os.chdir('..')
    os.chdir('zeo++')

    import time # debugging
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


    print('TIME CHECK 4')

    # Applying the model next

    # Merging geometric information with get_MOF_descriptors files (lc_descriptors.csv, sbu_descriptors.csv, linker_descriptors.csv)

    # from IPython.display import display # debugging

    lc_df = pd.read_csv("../../temp_file_creation/RACs/lc_descriptors.csv") # change addresses on different computer
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

    os.system('python solvent_ANN.py > solvent_prediction.txt')
    # import for_GT
    # prediction = for_GT.main()

    f = open("solvent_prediction.txt", "r")
    line = f.read()
    line = line.split('[')
    line = line[2]
    line = line.split(']')
    prediction = line[0] # isolating just the prediction, since the model spits out the prediction like [[PREDICTION]], as in, in hard brackets
    f.close()

    print('TIME CHECK 6')

    return prediction

@app.route('/predict_thermal_stability', methods=['POST']) # Gianmarco Terrones addition
def ts_predict():
    # Generates thermal stability prediction 
    # To do this, need to generate RAC featurization and Zeo++ geometry information for the MOF
    # Then, apply Aditya's model to make prediction

    print('TIME CHECK 1')

    # To begin, always go to main directory (this directory will vary depending on computer)
    os.chdir("/Users/gianmarcoterrones/Research/mofSimplify/")

    # Grab data
    mydata = json.loads(flask.request.get_data())

    os.chdir("temp_file_creation") # changing directory

    # Write the data back to a cif file
    cif_file = open('temp_cif.cif', 'w')
    cif_file.write(mydata)
    cif_file.close()

    # delete the RACs folder, then remake it (to start fresh for this prediction)
    shutil.rmtree('RACs')
    os.mkdir('RACs')

    os.chdir("RACs") # move to RACs folder

    print('TIME CHECK 2')

    # Next, running MOF featurization
    try:
        get_primitive('../temp_cif.cif', 'temp_cif_primitive.cif');
    except ValueError:
        return 'FAILED'

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

    print('TIME CHECK 3')

    # At this point, have the RAC featurization. Need geometry information next.

    # Run Zeo++
    os.chdir('..')
    os.chdir('zeo++')

    import time # debugging
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


    print('TIME CHECK 4')

    # Applying the model next

    # Merging geometric information with get_MOF_descriptors files (lc_descriptors.csv, sbu_descriptors.csv, linker_descriptors.csv)

    lc_df = pd.read_csv("../../temp_file_creation/RACs/lc_descriptors.csv") # change addresses on different computer
    sbu_df = pd.read_csv("../../temp_file_creation/RACs/sbu_descriptors.csv")
    linker_df = pd.read_csv("../../temp_file_creation/RACs/linker_descriptors.csv")

    lc_df = lc_df.mean().to_frame().transpose() # averaging over all rows. Convert resulting Series into a Dataframe, then transpose
    sbu_df = sbu_df.mean().to_frame().transpose()
    linker_df = linker_df.mean().to_frame().transpose()

    merged_df = pd.concat([geo_df, lc_df, sbu_df, linker_df], axis=1)
    merged_df.to_csv('../merged_descriptors.csv',index=False) # written in /temp_file_creation

    os.chdir('..')
    os.chdir('..')
    os.chdir('model/thermal/ANN')

    print('TIME CHECK 5')

    os.system('python thermal_ANN.py > thermal_prediction.txt')

    f = open("thermal_prediction.txt", "r")
    prediction = f.read()
    f.close()

    print('TIME CHECK 6')

    return prediction

@app.route('/get_components', methods=['POST']) # Gianmarco Terrones addition
def get_components():
    # Uses Aditya's MOF code to get linkers and sbus
    # Returns a dictionary with the linker and sbu xyz files's text, along with information about the number of linkers and sbus

    # To begin, always go to main directory (this directory will vary depending on computer)
    os.chdir("/Users/gianmarcoterrones/Research/mofSimplify/");

    # Grab data
    mydata = json.loads(flask.request.get_data());

    os.chdir("temp_file_creation"); # changing directory

    # Write the data back to a cif file
    cif_file = open('temp_cif.cif', 'w');
    cif_file.write(mydata);
    cif_file.close();


    # delete the RACs folder, then remake it (to start fresh for this prediction)
    shutil.rmtree('RACs');
    os.mkdir('RACs');

    os.chdir("RACs"); # move to RACs folder

    # Next, running MOF featurization
    try:
        get_primitive('../temp_cif.cif', 'temp_cif_primitive.cif');
    except ValueError:
        return 'FAILED'

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

    # At this point, have the RAC featurization. 

    # will return a json object
    # the fields are string representations of the linkers and sbus, however many there are

    dictionary = {};
    
    linker_num = 0;
    while True:
        if not os.path.exists('linkers/temp_cif_primitive_linker_' + str(linker_num) + '.xyz'):
            break
        else:
            linker_file = open('linkers/temp_cif_primitive_linker_' + str(linker_num) + '.xyz', 'r');
            linker_info = linker_file.read();
            linker_file.close();

            dictionary['linker_' + str(linker_num)] = linker_info;

            linker_num = linker_num + 1;


    sbu_num = 0;
    while True:
        if not os.path.exists('sbus/temp_cif_primitive_sbu_' + str(sbu_num) + '.xyz'):
            break
        else:
            sbu_file = open('sbus/temp_cif_primitive_sbu_' + str(sbu_num) + '.xyz', 'r');
            sbu_info = sbu_file.read();
            sbu_file.close();

            dictionary['sbu_' + str(sbu_num)] = sbu_info;

            sbu_num = sbu_num + 1;


    dictionary['total_linkers'] = linker_num;
    dictionary['total_sbus'] = sbu_num;


    os.chdir("linkers"); # move to linkers folder

    # Identifying which linkers and sbus have different connectivities

    # Code below uses molecular graph determinants 
    # two ligands that are the same (via connectivity) will have the same molecular graph determinant. 
    # Molecular graph determinant fails to distinguish between isomers, but so would RCM (Reverse Cuthill McKee)

    # This simple script is meant to be run within the linkers directory, and it will give a bunch of numbers. 
    # If those numbers are the same, the linker is the same, if not, the linkers are different, etc


    from molSimplify.Classes.mol3D import mol3D
    import glob
    MOF_of_interest = 'temp_cif_primitive'
    XYZs = sorted(glob.glob('*'+MOF_of_interest+'*xyz'))
    det_list = []

    for xyz in XYZs:
        net = xyz.replace('xyz', 'net') # substring replacement; getting the appropriate .net file
        linker_mol = mol3D()
        linker_mol.readfromxyz(xyz)
        with open(net,'r') as f:
            data = f.readlines()
        for i, line in enumerate(data):
            if i==0:
                # Skip first line
                continue
            elif i == 1:
                graph = np.array([[int(val) for val in line.strip('\n').split(',')]])
            else:
                graph = np.append(graph, [np.array([int(val) for val in line.strip('\n').split(',')])],axis=0)
        linker_mol.graph = graph
        safedet = linker_mol.get_mol_graph_det(oct=False)
        det_list.append(safedet)
    #### linkers with the same molecular graph determinant are the same
    #### molecular graph determinant does not catch isomers
    linker_det_list = det_list

    unique_linker_det = set(linker_det_list) # getting the unique determinants
    unique_linker_indices = []
    for item in unique_linker_det:
        unique_linker_indices.append(linker_det_list.index(item)) # indices of the unique linkers in the list of linkers



    os.chdir("../sbus"); # move to sbus folder

    XYZs = sorted(glob.glob('*'+MOF_of_interest+'*xyz'))
    det_list = []
    for xyz in XYZs:
        net = xyz.replace('xyz', 'net') # substring replacement; getting the appropriate .net file
        linker_mol = mol3D()
        linker_mol.readfromxyz(xyz)
        with open(net,'r') as f:
            data = f.readlines()
        for i, line in enumerate(data):
            if i==0:
                # Skip first line
                continue
            elif i == 1:
                graph = np.array([[int(val) for val in line.strip('\n').split(',')]])
            else:
                graph = np.append(graph, [np.array([int(val) for val in line.strip('\n').split(',')])],axis=0)
        linker_mol.graph = graph
        safedet = linker_mol.get_mol_graph_det(oct=False)
        det_list.append(safedet)

    sbu_det_list = det_list

    unique_sbu_det = set(sbu_det_list) # getting the unique determinants
    unique_sbu_indices = []
    for item in unique_sbu_det:
        unique_sbu_indices.append(sbu_det_list.index(item)) # indices of the unique sbus in the list of linkers


    # adding the unique indices to the dictionary
    dictionary['unique_linker_indices'] = unique_linker_indices;
    dictionary['unique_sbu_indices'] = unique_sbu_indices;

    json_object = json.dumps(dictionary, indent = 4);

    return json_object

# @app.route('/generate', methods=['POST'])
# def generate_mol():
#     # Grab data
#     mydata = json.loads(flask.request.get_data())

#     good_request = True

#     # Rename ligands appropriately
#     ligand_rename_dict = {'pyridine': 'pyr', 
#         'methyl isocyanide': 'misc',
#         'phenyl isocyanide': 'pisc',
#         'acetylacetonate': 'acac',
#         'bipyridine': 'bipy'}

#     for lig_type in ['ax1', 'ax2', 'eq']:
#         if mydata[lig_type] in ligand_rename_dict:
#             mydata[lig_type] = ligand_rename_dict[mydata[lig_type]]

#     ligoccs = []
#     ligs = []

#     if mydata['eq'] in licores: # Check for higher denticity
#         if isinstance(licores[mydata['eq']][2],list):
#             n = int(4/len(licores[mydata['eq']][2]))
#             for item in range(n):
#                 ligoccs.append(1)
#                 ligs.append(mydata['eq'])
#         else: # Monodentate
#             for item in range(4):
#                 ligoccs.append(1)
#                 ligs.append(mydata['eq'])
#     else: # Force monodentate for now
#         for item in range(4):
#             ligoccs.append(1)
#             ligs.append(mydata['eq'])

#     ligs.append(mydata['ax1'])
#     ligs.append(mydata['ax2'])
#     ligoccs.append(1)
#     ligoccs.append(1)

#     ligoccs = ','.join([str(x) for x in ligoccs])
#     if any([True for x in ligs if len(x) == 0]): # Catch cases where empty ligand passed.
#         good_request = False

#     ligs = ','.join([str(x) for x in ligs])
#     print(ligs,ligoccs)
#     # Generates an xyz file from parameters provided in POST request
#     rundir = os.path.join(os.getcwd(), 'geos/')
#     jobname = 'run_generate_query'
#     mytext = string.Template('''-rundir $rundir
# -ffoption no
# -skipANN True
# -distort 0
# -name $jobname
# -coord 6
# -core $metal
# -ligocc $ligoccs
# -geometry oct
# -spin $spin
# -ligloc True
# -oxstate $ox
# -lig $ligs
# -ff uff''')
#     mytext = mytext.substitute(rundir=rundir, metal=mydata['metal'], spin=mydata['spin'], ox=mydata['ox'], ligoccs=ligoccs, ligs=ligs, jobname=jobname)
#     inputstring_to_dict = lambda s: {i[0]:' '.join(i[1:]) for i in [i.split(' ') for i in s.split('\n')]}
#     mytext_dict = inputstring_to_dict(mytext)
#     try:
#         strfiles, emsg, this_diag = startgen_pythonic(mytext_dict)
#         print("printing xyz")
#         # print(this_diag.mol.writexyz('', writestring=True))
#         if good_request: 
#             outstring = this_diag.mol.writexyz('', writestring=True)
#         else:
#             outstring = mydata['geometry']
#     except UnboundLocalError:
#         print('CAUGHT UNBOUND LOCAL ERROR')
#         good_request = False
#         outstring = mydata['geometry']

#     http_response = {}
#     http_response['geometry'] = outstring
#     if good_request:
#         http_response['message'] = "Geometry Successfully Generated!"
#     else:
#         http_response['message'] = "Please either specify a valid monodentate SMILES string or select a pre-populated ligand."

#     return jsonify(http_response)
    



# @app.route('/nn_predict', methods=['POST'])
# def serve_nn_prediction():
#     # Run an NN prediction for the xyz file, ox state, and HFX contained in the POST request
#     try:
#         mydata = json.loads(flask.request.get_data())
#         xyzstr = mydata['geometry']
#         mymol = ms_mol3D.mol3D()
#         mymol.readfromstring(xyzstr)
#         rac_names, rac_vals = ms_RAC.get_descriptor_vector(mymol)
#         mydict = {rac_name:rac_val for rac_name, rac_val in zip(rac_names, rac_vals)}
#         mydict['alpha'] = float(mydata['hfx'])
#         mydict['ox'] = int(mydata['ox'])
#         mytable = pd.DataFrame([pd.Series(mydict)])
# 	    # Local ANN prediction
#         start_time = time.time()
#         mytable = perform_ANN_prediction(mytable, 'split')
#         SSE_prediction = mytable.split_prediction.iloc[0]

# 	    # Sketchy math to find ground state spin
#         quantum_spins = {1: '0', 2: '1/2', 3: '1', 4: '3/2', 5: '2', 6: '5/2'}
#         mult = int(mydata['spin'])
#         ground_mult = 6 - mult if SSE_prediction < 0 else mult
#         quantum_spin_str = quantum_spins[ground_mult]
#         time_taken = time.time() - start_time
#         myresult = results_string % (SSE_prediction, quantum_spin_str, time_taken)
#         http_response = {}
#         http_response['resulttext'] = myresult
#         http_response['result'] = str(SSE_prediction) 
#         return jsonify(http_response)
#     except:
#         http_response = {}
#         http_response['resulttext'] = 'Error'
#         http_response['result'] = str(-24.5) 
#         return jsonify(http_response)

# # Version 1 - KDE
# def make_plot(x1):
#     source = ColumnDataSource(datadf)
#     print(datadf.columns.values)
#     x_min = min(x1, min(datadf.sse.values))
#     x_max = max(x1, max(datadf.sse.values))
#     x_range = x_max - x_min
#     x_min, x_max = (x_min - 0.05*x_range, x_max + 0.05*x_range)
#     p = figure(title = "Your Complex Spin Splitting Energy Compared to Training Data", 
#                sizing_mode="scale_both", plot_width=400, plot_height=200, x_axis_type=None, x_range=(x_min, x_max))
#     p.yaxis.axis_label = 'KDE of Training Data'
#     p.line('sse', 'kde', source=source, line_width=2)
#     vertical = Span(location=x1,dimension='height',
#                     line_color='green',line_dash='dashed',line_width=3)
#     p.yaxis.major_tick_line_color = None  # turn off y-axis major ticks
#     p.yaxis.minor_tick_line_color = None  # turn off y-axis minor ticks
#     p.yaxis.major_label_text_font_size = '0pt'  # turn off y-axis tick labels
#     p.xgrid.grid_line_color = None
#     p.ygrid.grid_line_color = None
#     p.add_layout(vertical)
#     ticker = SingleIntervalTicker(interval=10, num_minor_ticks=2)
#     xaxis = LinearAxis(ticker=ticker)
#     p.add_layout(xaxis, 'below')
#     p.xaxis.axis_label = 'Spin Splitting Energy (kcal/mol)'
#     return p

# # Version 2 - PCA
# def make_plotpca(sse,geometry,ox,alpha):
#     print(pca_plot_df.columns.values)
#     ##### Apply Data
#     my_mol = ms_mol3D.mol3D()
#     my_mol.readfromstring(geometry)
#     RACs = my_mol.get_features()
#     RACs['ox'] = ox
#     RACs['alpha'] = alpha
#     new_vect = np.array([RACs[x] for x in pca_variables])
#     plot_vals = pca_model.transform(np.array(new_vect).reshape(1,-1))
#     x1 = plot_vals[0][0] # New X
#     y1 = plot_vals[0][1] # New Y
#     ########
#     x_min = min(x1, min(pca_plot_df.PC1.values))
#     x_max = max(x1, max(pca_plot_df.PC1.values))
#     y_min = min(y1, min(pca_plot_df.PC2.values))
#     y_max = max(y1, max(pca_plot_df.PC2.values))
#     x_range = x_max - x_min
#     y_range = y_max - y_min
#     x_min, x_max = (x_min - 0.05*x_range, x_max + 0.05*x_range)
#     y_min, y_max = (y_min - 0.05*y_range, y_max + 0.05*y_range)
#     #### Colormap
#     colormax = max(np.abs(sse),np.abs(pca_plot_df['Spin Splitting Energy (kcal/mol)'].values).max())
#     colormax = 50
#     mapper = LinearColorMapper(palette=cmap_bokeh, low=-colormax, high=colormax)
#     colors = {'field':np.array(list(pca_plot_df['Spin Splitting Energy (kcal/mol)'].values) + [sse]),
#                 'transform':mapper}
#     cticker = SingleIntervalTicker(interval=10, num_minor_ticks=0)
#     color_bar = ColorBar(color_mapper=mapper, ticker=cticker, label_standoff=5, 
#                          border_line_color=None, location=(0,0))#, title='SSE (kcal/mol)')
#     ##### Plotting
#     source = ColumnDataSource({
#         'PC1':pca_plot_df.PC1.values,
#         'PC2':pca_plot_df.PC2.values,
#         'chemname':pca_plot_df['Chemical Name'].values,
#         'color': pca_plot_df['Spin Splitting Energy (kcal/mol)'].values})
#     TOOLS="crosshair,pan,wheel_zoom,zoom_in,zoom_out,box_zoom,reset,tap,"
#     p = figure(title = "Your Complex (green) Compared to Training Data in Feature Space", 
#                sizing_mode="scale_both", plot_width=400, plot_height=400,
#                 x_range=(x_min, x_max),y_range=(y_min, y_max),tools=TOOLS)
#     # p.line('sse', 'kde', source=source, line_width=2)
#     source2 = ColumnDataSource({
#         'PC1':[x1],
#         'PC2':[y1],
#         'chemname':['Your Complex'],
#         'color': [sse]})
#     p.circle('PC1','PC2',source=source,fill_color={'field':'color','transform':mapper},line_color={'field':'color','transform':mapper},
#              size=10)
#     p.circle('PC1','PC2',source=source2,fill_color={'field':'color','transform':mapper},line_color='mediumseagreen',
#              size=20,line_width=3)
#     # Datalabels with hover animation.
#     p.add_tools(HoverTool(
#         tooltips = [('Chemical Name', '@chemname{%s}'),
#                      ('Spin Splitting Energy (kcal/mol)', '@color{%0.2d}'),
#                      ],
#         formatters={ 'chemname':'printf',
#             'color': 'printf'
#         }
#     ))
#     p.yaxis.major_tick_line_color = None  # turn off y-axis major ticks
#     p.yaxis.minor_tick_line_color = None  # turn off y-axis minor ticks
#     p.xaxis.major_tick_line_color = None  # turn off x-axis major ticks
#     p.xaxis.minor_tick_line_color = None  # turn off x-axis minor ticks
#     p.yaxis.major_label_text_font_size = '0pt'  # turn off y-axis tick labels
#     p.xaxis.major_label_text_font_size = '0pt' # turn off x-axis tick labels
#     p.xgrid.grid_line_color = None # Remove grid
#     p.ygrid.grid_line_color = None # Remove grid
#     p.outline_line_width = 2
#     p.outline_line_alpha = 1
#     p.outline_line_color = "black"
#     p.xaxis.axis_label = 'PC1'
#     p.yaxis.axis_label = 'PC2'
#     p.add_layout(color_bar,'right')
#     return p

# @app.route('/plot', methods=['POST'])
# def plot():
#     mydata = json.loads(flask.request.get_data())
#     plt = make_plot(float(mydata['sseplot'])) # V1 KDE
#     return file_html(plt,CDN,'my plot')

# @app.route('/plotpca', methods=['POST'])
# def plotpca():
#     mydata = json.loads(flask.request.get_data())
#     plt = make_plotpca(float(mydata['sseplot']),mydata['geometry'],
#                     mydata['ox'],mydata['hfx'])
#     return file_html(plt,CDN,'my plot pca')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
