import os
import pandas as pd
import json
import corepytools as corepy
#import sys
import lasio
from scipy.interpolate import interp1d
import numpy as np


# Attribute_merge.py is run after settings.py
# Attribute_merge.py puts in limits of detection, filters data by formation, and adds outlier information
# Attribute_merge.py searches for attribute and wireline data files and merges them into one .csv file

# Output: adds attribute csv files in //CorePy/CoreOutput/CoreName/<Formation>

# Root_path, Run_settings, and Corebeta and the two .json core settings files with all input parameters
Root_path = os.path.dirname(os.getcwd())
Run_settings=json.load(open(os.path.join(Root_path + '/CorePycodes/' + 'Run_settings' + '.json')))
Corebeta=json.load(open(os.path.join(Root_path + '/CoreData/CoreBeta/'   +  Run_settings['CoreOfStudy']  +'.json')))

# Formation_names is an expansion idea to select sub-Formations
# Creates a str variable to select Formation-specific rows from csv input file. 
# For now Formation_names is Run_settings["Formation"]
Formation_names=corepy.Formation_names(Run_settings["Formation"],Run_settings["Formation_2"])

# RootDir(corename, Formation_names) established the output folder structure
dirName=corepy.RootDir(Corebeta["corename"], Formation_names) 
corepy.RootDir(Run_settings['CoreOfStudy'], Formation_names)
corepy.MakeXRFdf(Run_settings['CoreOfStudy'],Run_settings["elements"],Run_settings["outlier_multiplier"],Run_settings["Depth_model"],Formation_names)
coredata=corepy.MakeXRFdf(Run_settings['CoreOfStudy'],Run_settings["elements"],Run_settings["outlier_multiplier"],Run_settings["Depth_model"],Formation_names)

# write .csv file here  in case there is no attribute data
coredata.to_csv (os.path.join(dirName + '/' +  Run_settings["CoreOfStudy"] + '_' + Formation_names + '.csv'))

# Searches for all csv files in attribute folder. The attribute data have to be depth references (core, box, inch) to match
Attribute_dir = os.path.join(Root_path + '/CoreData/CoreAttributes/'   +  Run_settings['CoreOfStudy'])


#Not all core have attribute data. This if state ends this script if there is no attribute fodler for the core

if str(os.path.isdir(Attribute_dir)) == 'True':

    all_files = os.listdir(Attribute_dir)    
    csv_files = list(filter(lambda f: f.endswith('.csv'), all_files))

    XRF_file = coredata

    Merged_file=XRF_file
    # Loop over the attribute files and merge on Core-Box-Inch
    for i in range(len(csv_files)):
        Attribute_file = pd.read_csv(os.path.join(Attribute_dir + '/' + csv_files[i]))
        # Merging adds duplicate file names so I use these two lines to remove duplicate names
        Merged_file = pd.merge(Merged_file, Attribute_file, how='left', on=['Core', 'Box', 'Inch'],suffixes=('', '_drop'))  
        Merged_file.drop([col for col in Merged_file.columns if 'drop' in col], axis=1, inplace=True)


    Merged_file.to_csv (os.path.join(dirName + '/' +  Run_settings["CoreOfStudy"] + '_' + Formation_names + '.csv'))
    
    coredata=Merged_file

# import LAS file if present
# calulates an wireline log value for each log at the XRF depth

API= Corebeta['API']
LAS_file_path=os.path.join(Root_path + '/CoreData/WirelineLogs/' + str(API) + '.las')

if str(os.path.isfile(LAS_file_path)) == 'True':

    las = lasio.read(LAS_file_path)

    wirelinedata=las.df()
    wirelinedata=wirelinedata.reset_index() # set up so that the first column is renamed 'DEPT' to keep it simple moving forward
    wirelinedata.rename(columns={ wirelinedata.columns[0]: "DEPT" }, inplace= True)

    wirelinedata = wirelinedata[wirelinedata['DEPT'] < max(coredata['Wireline_Depth'])]
    wirelinedata = wirelinedata[wirelinedata['DEPT'] > min(coredata['Wireline_Depth'])]


    wirelinedata.to_csv (os.path.join(dirName   + '/' +  Run_settings['CoreOfStudy'] +  '_LAS.csv'))


    Corebeta['WirelineLogs'] = las.keys()
    with open(os.path.join(Root_path + '/CoreData/CoreBeta/'   + Run_settings['CoreOfStudy']  + '.json'), 'w') as f:    
        json.dump(Corebeta, f)  

    df=pd.DataFrame(coredata['Wireline_Depth'])
    
    #for i in range (0,len(Corebeta['WirelineLogs_NeuralModel'])):
    for i in range (0,len(Corebeta['WirelineLogs'])):
        x=wirelinedata['DEPT']  # original wireline log depth is always called DEPT
        #y=wirelinedata[Corebeta['WirelineLogs_NeuralModel'][i]] # wireline log attribute being cycled over
        y=wirelinedata[Corebeta['WirelineLogs'][i]] # wireline log attribute being cycled over
        f = interp1d(x,y, bounds_error=False, fill_value=-10, kind='linear')

        new_data = np.array([coredata['Wireline_Depth'] , f(coredata['Wireline_Depth'] )])
        new_data=np.transpose(new_data)
    
        #df[Corebeta['WirelineLogs_NeuralModel'][i]] =  new_data[:, [1]]
        df[Corebeta['WirelineLogs'][i]] =  new_data[:, [1]]

    CoreWirelinedata = (pd.merge(coredata, df, on='Wireline_Depth')) # merge orriginal coredata XRF file with new wireline log values
    CoreWirelinedata.to_csv (os.path.join(dirName + '/' +  Run_settings['CoreOfStudy'] + '_' + Formation_names + '.csv'))
