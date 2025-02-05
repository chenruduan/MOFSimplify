import os, sys
import pandas as pd
import numpy as np
import pickle
import json
import tensorflow as tf
from functools import partial
from hyperopt import hp, tpe, fmin, Trials, STATUS_OK
from keras.callbacks import EarlyStopping
import sklearn
from molSimplifyAD.retrain.nets import build_ANN, auc_callback, cal_auc, compile_model
from molSimplifyAD.retrain.model_optimization import train_model_hyperopt
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

def normalize_data(df_train, df_test, fnames, lname, unit_trans=1, debug=False):
    _df_train = df_train.copy().dropna(subset=fnames+lname)
    _df_test = df_test.copy().dropna(subset=fnames+lname)
    X_train, X_test = _df_train[fnames].values, _df_test[fnames].values
    y_train, y_test = _df_train[lname].values, _df_test[lname].values
    if debug:
        print("training data reduced from %d -> %d because of nan." % (len(df_train), y_train.shape[0]))
        print("test data reduced from %d -> %d because of nan." % (len(df_test), y_test.shape[0]))
    x_scaler = sklearn.preprocessing.StandardScaler()
    x_scaler.fit(X_train)
    X_train = x_scaler.transform(X_train)
    X_test = x_scaler.transform(X_test)
    y_train = np.array([1 if x == 1 else 0 for x in y_train.reshape(-1, )])
    y_test = np.array([1 if x == 1 else 0 for x in y_test.reshape(-1, )])
    return X_train, X_test, y_train, y_test, x_scaler

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

path = os.getcwd()+'/'+str(sys.argv[1])
df_train_all = pd.read_csv(path+"/train.csv").append(pd.read_csv(path+"/val.csv"))
df_train = pd.read_csv(path+"/train.csv")
df_train = df_train.loc[:, (df_train != df_train.iloc[0]).any()]
df_val = pd.read_csv(path+"/val.csv")
df_test = pd.read_csv(path+"/test.csv")
features = [val for val in df_train.columns.values if val in RACs+geo]

df_train = standard_labels(df_train, key="flag")
df_val = standard_labels(df_val, key="flag")
df_test = standard_labels(df_test, key="flag")
df_train_all = standard_labels(df_train_all, key="flag")

X_train, X_test, y_train, y_test, x_scaler = normalize_data(df_train, df_test, features, ["flag"], unit_trans=1, debug=False)
X_train, X_val, y_train, y_val, x_scaler = normalize_data(df_train, df_val, features, ["flag"], unit_trans=1, debug=False)
X_train.shape, y_train.reshape(-1, ).shape

regression_target = 'flag'
steps = 50
epochs = 1000

with open('best_flag','rb') as f:
    hyperspace = pickle.load(f)

model = build_ANN(hyperspace, X_train.shape[-1], ['flag'], regression=False)
val_data = [X_val, y_val]
earlystop = EarlyStopping(monitor='val_loss',
                          min_delta=0.000001,
                          patience=hyperspace['patience'],
                          verbose=2)
lname = ['flag']
cb = [earlystop]
if len(lname) > 1:
    for ii, ln in enumerate(lname):
        cb += [auc_callback(training_data=(X_train, y_train[ii]), validation_data=(X_val, y_val[ii]), ind=ii)]
else:
    cb += [auc_callback(training_data=(X_train, y_train), validation_data=(X_val, y_val))]
history = model.fit(X_train, y_train,
                    epochs=epochs,
                    verbose=2,
                    batch_size=hyperspace['batch_size'],
                    validation_data=val_data,
                    callbacks=cb)


model.save('final_model_flag_few_epochs.h5')

with open('final_model_history_few_epochs','wb') as f:
    pickle.dump(history,f)
