import os, sys
import pandas as pd
import numpy as np
import pickle
import json
import tensorflow as tf
from functools import partial
from keras.callbacks import EarlyStopping
import sklearn
import keras.backend as K
#from molSimplifyAD.retrain.nets import build_ANN, auc_callback, cal_auc, compile_model
#from molSimplifyAD.retrain.model_optimization import train_model_hyperopt
import numpy as np
import pandas as pd
import sklearn.preprocessing
from scipy.stats import pearsonr, spearmanr
import sys
import os
import json
import pickle

blue = "rgba(0, 0, 255, 1)"
red = "rgba(255, 0, 0, 1)"
green = "rgba(0, 196, 64, 1)"
gray = "rgba(140, 140, 140, 1)"

def normalize_data(df_train, df_newMOF, fnames, lname, unit_trans=1, debug=False): # assumes gets Pandas dataframes with MOFs as rows and features as columns
    _df_train = df_train.copy().dropna(subset=fnames+lname)
    _df_newMOF = df_newMOF.copy().dropna(subset=fnames) #+lname)
    X_train, X_newMOF = _df_train[fnames].values, _df_newMOF[fnames].values
    # y_train, y_test = _df_train[lname].values, _df_test[lname].values
    y_train = _df_train[lname].values
    if debug:
        print("training data reduced from %d -> %d because of nan." % (len(df_train), y_train.shape[0]))
    #    print("test data reduced from %d -> %d because of nan." % (len(df_test), y_test.shape[0]))
    x_scaler = sklearn.preprocessing.StandardScaler()
    x_scaler.fit(X_train)
    X_train = x_scaler.transform(X_train)
    X_newMOF = x_scaler.transform(X_newMOF)
    y_scaler = sklearn.preprocessing.StandardScaler()
    y_scaler.fit(y_train)
    y_train = y_scaler.transform(y_train)
    # y_test = y_scaler.transform(y_test)
    # return X_train, X_test, y_train, y_test, x_scaler, y_scaler
    return X_train, X_newMOF, y_train, x_scaler, y_scaler

def optimize(X, y, y_name,
             regression=False, hyperopt_step=200,
             arch=False, epochs=2000,
             X_val=False, y_val=False,
             model=False, path=False):
    np.random.seed(1234)
    if arch == False:
        architectures = [(200, 200),
                         (300, 300),
                         (500, 500),
                         (100, 100, 100),
                         (200, 200, 200),
                         (300, 300, 300),
                         (500, 500, 500)]
    else:
        architectures = [arch]
    batches = [10, 20, 30, 50, 100, 200, 300, 500]
    space = {'lr': hp.uniform('lr', 1e-5, 1e-3),
             'drop_rate': hp.uniform('drop_rate', 0, 0.5),
             'reg': hp.loguniform('reg', np.log(1e-5), np.log(5e-1)),
             'batch_size': hp.choice('batch_size', batches),
             'hidden_size': hp.choice('hidden_size', architectures),
             'beta_1': hp.uniform('beta_1', 0.75, 0.99),
             'decay': hp.loguniform('decay', np.log(1e-5), np.log(1e-1)),
             'amsgrad': True,
             'patience': 200,
             }
    objective_func = partial(train_model_hyperopt,
                             X=X,
                             y=y,
                             lname=y_name,
                             regression=regression,
                             epochs=epochs,
                             X_val=X_val,
                             y_val=y_val,
                             model=model,
                             path=path)
    trials = Trials()
    best_params = fmin(objective_func,
                       space,
                       algo=tpe.suggest,
                       trials=trials,
                       max_evals=hyperopt_step,
                       rstate=np.random.RandomState(0)
                       )
    best_params.update({'hidden_size': architectures[best_params['hidden_size']],
                        'batch_size': batches[best_params['batch_size']],
                        'amsgrad': True,
                        'patience': 200,
                        })
    return trials, best_params

def standard_labels(df, key="flag"):
    flags = [1 if row[key] == 1 else 0 for _, row in df.iterrows()]
    df[key] = flags
    return df
def precision(y_true, y_pred):
    true_positives = K.sum(K.round(K.clip(y_true * y_pred, 0, 1)))
    predicted_positives = K.sum(K.round(K.clip(y_pred, 0, 1)))
    precision = true_positives / (predicted_positives + K.epsilon())
    return precision
def recall(y_true, y_pred):
    true_positives = K.sum(K.round(K.clip(y_true * y_pred, 0, 1)))
    possible_positives = K.sum(K.round(K.clip(y_true, 0, 1)))
    recall = true_positives / (possible_positives + K.epsilon())
    return recall
def f1(y_true, y_pred):
    p = precision(y_true, y_pred)
    r = recall(y_true, y_pred)
    return 2 * ((p * r) / (p + r + K.epsilon()))
RACs = ['D_func-I-0-all','D_func-I-1-all','D_func-I-2-all','D_func-I-3-all',
 'D_func-S-0-all', 'D_func-S-1-all', 'D_func-S-2-all', 'D_func-S-3-all',
 'D_func-T-0-all', 'D_func-T-1-all', 'D_func-T-2-all', 'D_func-T-3-all',
 'D_func-Z-0-all', 'D_func-Z-1-all', 'D_func-Z-2-all', 'D_func-Z-3-all',
 'D_func-chi-0-all', 'D_func-chi-1-all', 'D_func-chi-2-all',
 'D_func-chi-3-all', 'D_lc-I-0-all', 'D_lc-I-1-all', 'D_lc-I-2-all',
 'D_lc-I-3-all', 'D_lc-S-0-all', 'D_lc-S-1-all', 'D_lc-S-2-all',
 'D_lc-S-3-all', 'D_lc-T-0-all', 'D_lc-T-1-all', 'D_lc-T-2-all',
 'D_lc-T-3-all', 'D_lc-Z-0-all', 'D_lc-Z-1-all', 'D_lc-Z-2-all',
 'D_lc-Z-3-all', 'D_lc-chi-0-all', 'D_lc-chi-1-all', 'D_lc-chi-2-all',
 'D_lc-chi-3-all', 'D_mc-I-0-all', 'D_mc-I-1-all', 'D_mc-I-2-all',
 'D_mc-I-3-all', 'D_mc-S-0-all', 'D_mc-S-1-all', 'D_mc-S-2-all',
 'D_mc-S-3-all', 'D_mc-T-0-all', 'D_mc-T-1-all', 'D_mc-T-2-all',
 'D_mc-T-3-all', 'D_mc-Z-0-all', 'D_mc-Z-1-all', 'D_mc-Z-2-all',
 'D_mc-Z-3-all', 'D_mc-chi-0-all', 'D_mc-chi-1-all', 'D_mc-chi-2-all',
 'D_mc-chi-3-all', 'f-I-0-all', 'f-I-1-all', 'f-I-2-all', 'f-I-3-all',
 'f-S-0-all', 'f-S-1-all', 'f-S-2-all', 'f-S-3-all', 'f-T-0-all', 'f-T-1-all',
 'f-T-2-all', 'f-T-3-all', 'f-Z-0-all', 'f-Z-1-all', 'f-Z-2-all', 'f-Z-3-all',
 'f-chi-0-all', 'f-chi-1-all', 'f-chi-2-all', 'f-chi-3-all', 'f-lig-I-0',
 'f-lig-I-1', 'f-lig-I-2', 'f-lig-I-3', 'f-lig-S-0', 'f-lig-S-1', 'f-lig-S-2',
 'f-lig-S-3', 'f-lig-T-0', 'f-lig-T-1', 'f-lig-T-2', 'f-lig-T-3', 'f-lig-Z-0',
 'f-lig-Z-1', 'f-lig-Z-2', 'f-lig-Z-3', 'f-lig-chi-0', 'f-lig-chi-1',
 'f-lig-chi-2', 'f-lig-chi-3', 'func-I-0-all', 'func-I-1-all',
 'func-I-2-all', 'func-I-3-all', 'func-S-0-all', 'func-S-1-all',
 'func-S-2-all', 'func-S-3-all', 'func-T-0-all', 'func-T-1-all',
 'func-T-2-all', 'func-T-3-all', 'func-Z-0-all', 'func-Z-1-all',
 'func-Z-2-all', 'func-Z-3-all', 'func-chi-0-all', 'func-chi-1-all',
 'func-chi-2-all', 'func-chi-3-all', 'lc-I-0-all', 'lc-I-1-all', 'lc-I-2-all',
 'lc-I-3-all', 'lc-S-0-all', 'lc-S-1-all', 'lc-S-2-all', 'lc-S-3-all',
 'lc-T-0-all', 'lc-T-1-all', 'lc-T-2-all', 'lc-T-3-all', 'lc-Z-0-all',
 'lc-Z-1-all', 'lc-Z-2-all', 'lc-Z-3-all', 'lc-chi-0-all', 'lc-chi-1-all',
 'lc-chi-2-all', 'lc-chi-3-all', 'mc-I-0-all', 'mc-I-1-all', 'mc-I-2-all',
 'mc-I-3-all', 'mc-S-0-all', 'mc-S-1-all', 'mc-S-2-all', 'mc-S-3-all',
 'mc-T-0-all', 'mc-T-1-all', 'mc-T-2-all', 'mc-T-3-all', 'mc-Z-0-all',
 'mc-Z-1-all', 'mc-Z-2-all', 'mc-Z-3-all', 'mc-chi-0-all', 'mc-chi-1-all',
 'mc-chi-2-all', 'mc-chi-3-all']
geo = ['Df','Di', 'Dif','GPOAV','GPONAV','GPOV','GSA','POAV','POAV_vol_frac',
  'PONAV','PONAV_vol_frac','VPOV','VSA','rho']
 
other = ['cif_file','name','filename']


path = os.getcwd()+'/'
df_train_all = pd.read_csv(path+"/train.csv").append(pd.read_csv(path+"/val.csv"))
df_train = pd.read_csv(path+"/train.csv")
df_train = df_train.loc[:, (df_train != df_train.iloc[0]).any()]
# df_val = pd.read_csv(path+"/val.csv")
# df_test = pd.read_csv(path+"/test.csv")
# df_new = pd.read_csv(path+"/full_CoRE_MOF_feature_set_with_geo.csv")
df_newMOF = pd.read_csv('../../../temp_file_creation/merged_descriptors.csv') # Assume temp_file_creation/ in parent directory
features = [val for val in df_train.columns.values if val in RACs+geo]

X_train, X_newMOF, y_train, x_scaler, y_scaler = normalize_data(df_train, df_newMOF, features, ["T"], unit_trans=1, debug=False)
# X_train, X_val, y_train, y_val, x_scaler, y_scaler = normalize_data(df_train, df_val, features, ["T"], unit_trans=1, debug=False)
X_train.shape, y_train.reshape(-1, ).shape 
# X_new = x_scaler.transform(df_new[features].values)

regression_target = 'T'
steps = 200
import keras
import keras.backend as K
dependencies = {'precision':precision,'recall':recall,'f1':f1}
model = keras.models.load_model('final_model_T_few_epochs.h5',custom_objects=dependencies)
# train_pred = y_scaler.inverse_transform(model.predict(X_train))
# val_pred = y_scaler.inverse_transform(model.predict(X_val))
# test_pred = y_scaler.inverse_transform(model.predict(X_test))
# new_pred = y_scaler.inverse_transform(model.predict(X_new))
new_MOF_pred = y_scaler.inverse_transform(model.predict(X_newMOF))
new_MOF_pred = np.round(new_MOF_pred,1) # round to 1 decimal

# isolating just the prediction, since the model spits out the prediction like [[PREDICTION]], as in, in hard brackets
new_MOF_pred = str(new_MOF_pred)
new_MOF_pred = new_MOF_pred.split('[')
new_MOF_pred = new_MOF_pred[2]
new_MOF_pred = new_MOF_pred.split(']')
new_MOF_pred = new_MOF_pred[0]

# adding units
degree_sign= u'\N{DEGREE SIGN}'
new_MOF_pred = new_MOF_pred + degree_sign + 'C' # degrees Celsius

print(new_MOF_pred) # do not get rid of this print statement


# from sklearn.metrics import r2_score
# df_train['predicted'] = train_pred
# df_val['predicted'] = val_pred
# df_test['predicted'] = test_pred
# df_new['predicted'] = new_pred
# print(abs(df_train['predicted']-df_train['T']).mean(),'train',r2_score(df_train['T'],df_train['predicted']))
# print(abs(df_val['predicted']-df_val['T']).mean(),'val', r2_score(df_val['T'],df_val['predicted']))
# print(abs(df_test['predicted']-df_test['T']).mean(),'test', r2_score(df_test['T'],df_test['predicted']))
# print(df_train['predicted'].min())
# print(df_test['predicted'].min())
# print(df_val['predicted'].min())
# df_train.to_csv('train_with_predicted.csv',index=False)
# df_val.to_csv('val_with_predicted.csv',index=False)
# df_test.to_csv('test_with_predicted.csv',index=False)
# df_new.to_csv('CoRE_with_predicted_TGA.csv',index=False)
