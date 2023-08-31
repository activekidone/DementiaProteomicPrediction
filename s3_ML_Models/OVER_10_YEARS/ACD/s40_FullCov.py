

import numpy as np
import pandas as pd
from Utility.Training_Utilities import *
from Utility.DelongTest import delong_roc_test
from lightgbm import LGBMClassifier
from sklearn.metrics import roc_auc_score
import scipy.stats as stats
pd.options.mode.chained_assignment = None  # default='warn'

def get_top_pros(mydf):
    p_lst = mydf.p_delong.tolist()
    i = 0
    while((p_lst[i]<0.05)|(p_lst[i+1]<0.05)):
        i+=1
    return i

dpath = '/Volumes/JasonWork/Projects/AD_Proteomics/Data/'
outpath = '/Volumes/JasonWork/Projects/AD_Proteomics/Results/'
outputfile = outpath + 'ML_Modeling/OVER_10_YEARS/ACD/s40_FullCov.csv'

pro_f_df = pd.read_csv(outpath + 'ML/OVER_10_YEARS/ACD/AccAUC_TotalGain.csv')
nb_top_pros = get_top_pros(pro_f_df)
pro_f_lst = pro_f_df.Pro_code.tolist()[:nb_top_pros]
pro_df = pd.read_csv(dpath + 'Proteomics/ProteomicsData.csv', usecols = ['eid'] + pro_f_lst)
pro_dict = pd.read_csv(dpath + 'Proteomics/Raw/ProCode.csv', usecols = ['Pro_code', 'Pro_definition'])
target_df = pd.read_csv(dpath + 'TargetOutcomes/ACD/ACD_outcomes.csv', usecols = ['eid', 'target_y', 'BL2Target_yrs'])
cov_f_lst = ['age', 'sex', 'educ', 'apoe4', 'pm_time', 'rt_time']
cov_df = pd.read_csv(dpath + 'Covariates/CovData_normalized.csv', usecols = ['eid', 'Region_code'] + cov_f_lst)

mydf = pd.merge(target_df, pro_df, how = 'inner', on = ['eid'])
mydf = pd.merge(mydf, cov_df, how = 'left', on = ['eid'])
rm_idx = mydf.index[(mydf.BL2Target_yrs < 10) & (mydf.target_y == 1)]
mydf.drop(rm_idx, axis = 0, inplace = True)
mydf.reset_index(inplace = True, drop = True)
fold_id_lst = [i for i in range(10)]

my_params = {'n_estimators': 500,
             'max_depth': 15,
             'num_leaves': 10,
             'subsample': 0.7,
             'learning_rate': 0.01,
             'colsample_bytree': 0.7}

y_test_full = np.zeros(shape = [1,1])
for fold_id in fold_id_lst:
    test_idx = mydf['Region_code'].index[mydf['Region_code'] == fold_id]
    y_test_full = np.concatenate([y_test_full, np.expand_dims(mydf.iloc[test_idx].target_y, -1)])

tmp_f, AUC_cv_lst= [], []


tmp_f = cov_f_lst
AUC_cv = []
y_pred_full = np.zeros(shape = [1,1])
for fold_id in fold_id_lst:
    train_idx = mydf['Region_code'].index[mydf['Region_code'] != fold_id]
    test_idx = mydf['Region_code'].index[mydf['Region_code'] == fold_id]
    X_train, X_test = mydf.iloc[train_idx][tmp_f], mydf.iloc[test_idx][tmp_f]
    y_train, y_test = mydf.iloc[train_idx].target_y, mydf.iloc[test_idx].target_y
    my_lgb = LGBMClassifier(objective='binary', metric='auc', is_unbalance=True, n_jobs=4, verbosity=-1, seed=2020)
    my_lgb.set_params(**my_params)
    my_lgb.fit(X_train, y_train)
    y_pred_prob = my_lgb.predict_proba(X_test)[:, 1]
    AUC_cv.append(np.round(roc_auc_score(y_test, y_pred_prob), 3))
    y_pred_full = np.concatenate([y_pred_full, np.expand_dims(y_pred_prob, -1)])
auc_full = roc_auc_score(y_test_full[:, 0], y_pred_full[:, 0])
tmp_out = np.array([np.round(np.mean(AUC_cv), 3), np.round(np.std(AUC_cv), 3), np.round(auc_full, 3)] + AUC_cv)
AUC_cv_lst.append(tmp_out)
print((np.mean(AUC_cv), np.round(np.mean(AUC_cv), 3), np.round(auc_full, 3)))

myout = pd.DataFrame(AUC_cv_lst, columns = ['AUC_mean', 'AUC_std', 'AUC_full'] + ['AUC_' + str(i) for i in range(10)])
myout.to_csv(outputfile, index = False)

print('finished')

