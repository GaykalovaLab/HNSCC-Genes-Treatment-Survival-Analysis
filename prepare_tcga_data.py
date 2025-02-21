import argparse
import pandas as pd
import numpy as np
import math

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Transform data from TCGA csv to csv suitable for survival analysis",
        formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("-input_patient_csv", help="Clinical patient data", type=str, required=True)
    parser.add_argument("-input_genes_csv", help="Genetical patient data", type=str, required=True)
    parser.add_argument("-input_pfs_csv", help="Prediction free survival patient data", type=str, default="")

    parser.add_argument("-input_delimiter", help="Delimiter for input file", type=str, default=",")
    parser.add_argument("-list_of_genes", help="List of genes for analysis", type=str, default="")
    parser.add_argument("--age_levels", help="Age levels for analysis", type=str, default="53.29637234770705,62.506502395619435,70.3607118412046")
    parser.add_argument("-output_csv", help="Output CSV file", type=str, default="tcga_data2.csv")
    args = parser.parse_args()
    input_patient_csv = args.input_patient_csv
    input_delimiter = args.input_delimiter
    df = pd.read_csv(input_patient_csv, delimiter=input_delimiter)
    df_genes = pd.read_csv(args.input_genes_csv)
    diagnosis = "Head & Neck Squamous Cell Carcinoma"
    colnames = ['bcr_patient_barcode', 'histologic_diagnosis', 'anatomic_organ_subdivision', 'gender',
       'birth_days_to', 'margin_status', 'vital_status', 'last_contact_days_to', 'race',
       'death_days_to', 'hpv_status_p16', 'tobacco_smoking_history_indicator',
        'alcohol_history_documented','alcohol_consumption_frequency',
       'age_at_initial_pathologic_diagnosis.x', 'clinical_M', 'clinical_N',
       'clinical_T', 'clinical_stage.x',
       'days_to_initial_pathologic_diagnosis','ajcc_pathologic_tumor_stage','lymphovascular_invasion',
            'perineural_invasion']
    list_of_genes = args.list_of_genes.split(',')
    df_filtered = df
    #df_filtered = df[df['histologic_diagnosis'] == diagnosis]
    #drop column histological_diagnosis
    df_filtered = df_filtered[colnames]
    df_filtered = df_filtered.drop(columns=['histologic_diagnosis'])
    #fill hpv_16_status with 0 if nan
    df_filtered['p16'] = df_filtered['hpv_status_p16'].fillna(False)
    df_filtered['p16'] = df_filtered['p16'].apply(lambda x: 'Y' if x=='Positive' else 'N')


    #fill alcohol_consumption_frequency with 0 if nan
    df_filtered['alcohol_consumption_frequency'] = df_filtered['alcohol_consumption_frequency'].fillna(0)
    #fill death_days_to with last_contact_days_to if nan
    df_filtered['survival_in_days'] = df_filtered['death_days_to'].fillna(df_filtered['last_contact_days_to'])
    df_filtered.loc[df_filtered['survival_in_days'] == '0','survival_in_days'] = '1'
    #drop last_contact_days_to
    df_filtered = df_filtered.drop(columns=['last_contact_days_to'])
    df_filtered['status'] = df_filtered['vital_status'].apply(lambda x : True if x == 'Dead' else False)

    df_filtered.rename(columns={'gender':'sex'},inplace=True)
    #make all laters in values to lower with Upper first letter
    df_filtered['sex'] = df_filtered['sex'].apply(lambda x: x.lower().capitalize())
    #df_filtered = df_filtered.dropna(axis=0)
    diagnosis_groups_dict = {'Oral Cavity':['Oral Tongue','Floor of mouth','Buccal Mucosa',
                                            'Alveolar Ridge','Hard Palate','Oral Cavity','Lip'],
                             'Oropharynx':['Base of tongue','Tonsil','Oropharynx'],
                             'Hypopharynx':['Hypopharynx'],
                             'Larynx':['Larynx']}

    stage_groups_dict = {1: ['Stage I'],2:['Stage II'],3: ['Stage III'],4: ['Stage IV','Stage IVA','Stage IVB','Stage IVC']}
    vi_dict = {'Y': ['YES'],'N':['NO'],'Unknown' :['NA']}


    def apply_group_rename(x,groups_dict):
        for key,value in groups_dict.items():
            if x in value:
                return key


    def race_group(x):
        if x == 'WHITE':
            return 'white'
        elif x == 'BLACK OR AFRICAN AMERICAN':
            return 'black'
        elif x == "" or x is None or pd.isnull(x):
            return 'Unknown'
        else:
            return 'other'

    df_filtered['race'] = df_filtered['race'].apply(lambda x:race_group(x))
    df_filtered['cancer_type'] = df_filtered['anatomic_organ_subdivision'].apply(lambda x:apply_group_rename(x,diagnosis_groups_dict))
    df_filtered['anatomic_stage'] = df_filtered['ajcc_pathologic_tumor_stage'].apply(lambda x:apply_group_rename(x,stage_groups_dict))
    df_filtered['lvi'] = df_filtered['lymphovascular_invasion'].apply(lambda x:apply_group_rename(x,vi_dict))
    df_filtered['pni'] = df_filtered['perineural_invasion'].apply(lambda x:apply_group_rename(x,vi_dict))
    df_filtered['smoking'] = df_filtered['tobacco_smoking_history_indicator'].apply(lambda x:1 if x == 'smoker' else 0)
    df_filtered['alcohol'] = df_filtered['alcohol_history_documented'].apply(lambda x: 1 if x == 'YES' else (0 if x == 'NO' else np.nan))
    df_filtered['age'] = df_filtered['birth_days_to'].apply(lambda x: np.abs(x)/365.25)
    if args.age_levels:
        age_levels = sorted(args.age_levels.split(','),reverse=False)
        group_number = 0
        df_filtered['age_level'] = 0
        for group_number in range(0,len(age_levels)+1):
            if group_number == 0:
                al = age_levels[group_number]
                df_filtered.loc[df_filtered['age'] <= float(al),'age_level'] = float(group_number)
            elif group_number == len(age_levels):
                al = age_levels[group_number-1]
                df_filtered.loc[df_filtered['age'] > float(al),'age_level'] = float(group_number)
            else:
                al = age_levels[group_number-1]
                df_filtered.loc[(df_filtered['age'] > float(al)) & (df_filtered['age'] <= float(age_levels[group_number])),'age_level'] = float(group_number)



    for gene in list_of_genes:
        df_filtered["gene_"+gene]=False
    #cycle through all rows of table
    for index,row in df_filtered.iterrows():
        patient_id = row['bcr_patient_barcode']
        #filter gene data. Columns Tumor_Sample_Barcode should start from patient_id
        df_genes_filtered = df_genes[df_genes['Tumor_Sample_Barcode'].str.startswith(patient_id)]

        #cycle through all genes
        for gene in list_of_genes:
            #check if this gene is for this patient or no
            df_filtered.loc[index,"gene_"+gene] = gene in df_genes_filtered['Hugo_Symbol'].tolist()
    #compute number of nan values in each column


    col_to_drop = ['anatomic_organ_subdivision','birth_days_to','margin_status',
                   'tobacco_smoking_history_indicator' ,'alcohol_history_documented',
                   'alcohol_consumption_frequency', 'age_at_initial_pathologic_diagnosis.x',
                   'days_to_initial_pathologic_diagnosis','hpv_status_p16','vital_status','death_days_to',
                   'clinical_stage.x','clinical_M','clinical_N','clinical_T','ajcc_pathologic_tumor_stage',
                   'lymphovascular_invasion','perineural_invasion']
    #drop rows where survival_in_days <=0, convert survival days to int before
    def toint(x):
        try:
            return int(x)
        except:
            return -1
    df_filtered['survival_in_days'] = df_filtered['survival_in_days'].apply(lambda x: toint(x))
    df_filtered = df_filtered[df_filtered['survival_in_days'] > 0]
    df_filtered.drop(columns=col_to_drop,inplace=True)
    print(df_filtered.isnull().sum())
    #df_filtered = df_filtered.dropna(axis=0)

    #drop rows with missing values

    #print(pd.unique(df_filtered['anatomic_organ_subdivision']))
    if args.input_pfs_csv:
        df_pfs = pd.read_csv(args.input_pfs_csv)
        df_pfs = df_pfs[['bcr_patient_barcode','PFI.time.1','PFI.1']]
        df_filtered = pd.merge(df_filtered,df_pfs,on='bcr_patient_barcode')
        df_filtered.rename(columns={'PFI.time.1':'progression-free-time'},inplace=True)
        df_filtered.rename(columns={'PFI.1': 'progression-free-time-status'}, inplace=True)
        #replace '#N/A' with nan
        df_filtered['progression-free-time'] = df_filtered['progression-free-time'].replace('#N/A',np.nan)
        df_filtered['progression-free-time-status'] = df_filtered['progression-free-time-status'].replace('#N/A',np.nan)

    df_filtered.rename(columns={'bcr_patient_barcode':'patient_id'},inplace=True)
    df_filtered.to_csv(args.output_csv, index=False)
