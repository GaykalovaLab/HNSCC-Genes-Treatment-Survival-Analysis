import argparse
import pandas as pd
import numpy as np
import math

from fontTools.merge.util import first

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Transform data from initial csv to csv suitable for survival analysis",
        formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("-input_csv", help="Input CSV files", type=str, required=True)
    parser.add_argument("-input_delimiter", help="Delimiter for input file", type=str, default=",")
    parser.add_argument("-output_csv", help="Output CSV file", type=str, default="tdf.csv")
    parser.add_argument("-treatment_time_prefix", help="prefix of columns with date of treatment", type=str, default="treatment_time")
    parser.add_argument("-recc_time_prefix", help="prefix of columns with date of treatment", type=str, default="reccurence_time")
    parser.add_argument("-treatment_type_prefix", help="prefix of columns with type of treatment", type=str, default="treatment_type")
    parser.add_argument("-response_prefix", help="prefix of columns with response to treatment", type=str, default="response_")
    parser.add_argument("--verbose", help="Verbose level", type=int, default=2)
    args = parser.parse_args()
    input_csv = args.input_csv
    input_delimiter = args.input_delimiter
    df = pd.read_csv(input_csv, delimiter=input_delimiter)
    treatment_time_columns = df.filter(regex=args.treatment_time_prefix).columns
    recc_time_columns = df.filter(regex=args.recc_time_prefix).columns
    def fix_format(l):
        lout=[]
        for x in l:
            try:
                lout.append(int(x))
            except ValueError:
                if x == 'none' or x == 'unknown'or np.isnan(x):
                    lout.append(None)
                else:
                    print(f"Bad element in list {l} {x}")
        return lout
    df['treatment_time'] = df[treatment_time_columns].values.tolist()
    df['treatment_time'] = df['treatment_time'].apply(fix_format)
    df['recc_time'] = df[recc_time_columns].values.tolist()
    df['recc_time'] = df['recc_time'].apply(fix_format)

    treatment_type_columns = df.filter(regex=args.treatment_type_prefix).columns
    print(treatment_type_columns)
    df['treatment_type'] = df[treatment_type_columns].values.tolist()
    df['treatment_type'] = df['treatment_type'].apply(fix_format)
    response_columns = df.filter(regex=args.response_prefix).columns
    df['response_'] = df[response_columns].values.tolist()
    df['response_'] = df['response_'].apply(fix_format)

    for i in range(len(df['treatment_type'])):
        end_index = None
        if 'none' in df['treatment_type'][i]:
            end_index = df['treatment_type'][i].index('none')
        if 'none' in df['response_'][i]:
            end_index = df['response_'][i].index('none')
        if end_index is not None:
            df['treatment_type'][i] = df['treatment_type'][i][:end_index]
            df['response_'][i] = df['response_'][i][:end_index]
            df['treatment_time'][i] = df['treatment_time'][i][:end_index]
    j = 0
    transf_dataset = []
    list_of_lost_times = {}
    list_of_lost_repsonse_treatment = {}

    for row in df.iterrows():
        d = row[1]['treatment_time']  # list of times of treatment
        d = [x for x in d if x is not None]
        rt = row[1]['recc_time']
        rt = [x for x in rt if x is not None]
        if isinstance(d, str):
            print(f'Treatment time is string {d}')
        if any([x < -5000 for x in d]):
            list_of_lost_times[row[1]['patient_id']] = -1
            continue
        # continue if list contains None or NaN
        if any([x is None or math.isnan(x) for x in [d[0]]]):
            continue
        number_of_mutation = row[1].filter(regex='gene_').sum()
        #check correctnes of input data and generate response and treatment list for current patient
        resp_list = []
        treat_list = []
        if args.verbose > 1:
            print(f"Patient {row[1]['patient_id']} Times: {d} Response: {resp_list} Treatment: {treat_list}")
        for i in range(0, len(d)):
            if (d[i - 1] is None or math.isnan(d[i])) and not (d[i] is None or math.isnan(d[i])):
                list_of_lost_times[row[1]['patient_id']] = i
            if d[i - 1] is not None and not math.isnan(d[i]):
                try:
                    resp = float(row[1]['response_'][i])
                except (ValueError,TypeError) :
                    resp = row[1]['response_'][i]
                try:
                    treat = float(row[1]['treatment_type'][i])
                except (ValueError,TypeError):
                    treat = row[1]['treatment_type'][i]
                if isinstance(resp, str) or resp is None:
                    list_of_lost_repsonse_treatment[row[1]['patient_id']] = -3 * 10 - (i)

                resp_list.append(resp)
                if isinstance(treat, str) or treat is None:
                    list_of_lost_repsonse_treatment[row[1]['patient_id']] = -2 * 10 - (i)
                treat_list.append(treat)
        if d[0] > 0:
            d = [0] + d
            rt = [0] + rt
        if len(resp_list) != len(treat_list):
            raise RuntimeError(f"Internal error! Length of response and treatment list is different {len(resp_list)} {len(treat_list)}")
        if len(d) > len(resp_list) :
            resp_list = [None] + resp_list
            treat_list = [None] + treat_list
        #print(list_of_lost_repsonse_treatment)
        if args.verbose > 1:
            print(f"Patient {row[1]['patient_id']} {d} {resp_list} {treat_list}")
        treatment_number = 0
        for i in range(0, len(d)):
            treat_status = int(row[1]['status'])
            if len(rt) <= i+1:
                if treat_status == 1:
                    dft = row[1]['survival_in_days'] - d[i]
                    rt.append(row[1]['survival_in_days'])
                else:
                    dft = None
            else:
                dft = rt[i+1] - d[i]
            treat = treat_list[i]
            resp = resp_list[i]
            if not (resp is None or math.isnan(resp)):
                treatment_number += 1
            if treatment_number == 1:
                first_treatment = 1
            elif treatment_number > 1 and treatment_number < 4:
                first_treatment = 2
            else:
                first_treatment = 3

            new_row_tdf = {"tindex": i+1,"tnum": treatment_number,"treatment_group":first_treatment, "treatment_time": d[i],
                           "recc_time": rt[i], "response": resp, "treatment_type": treat,
                           "status": treat_status, "disease_free_time": dft, "patient_id": row[1]['patient_id'],
                           "anatomic_stage": row[1]['anatomic_stage'], "cancer_type": row[1]['cancer_type'],
                           "smoking": row[1]['smoking'], "alcohol_history": row[1]['alcohol_history'], "drugs": row[1]['drugs'],
                           "age_level": row[1]['age_level'], "number_of_mutation": number_of_mutation,
                           "sex": row[1]['sex'],
                           "p16": row[1]['p16'], 'race': row[1]['race'], 'patient_id': row[1]['patient_id'],
                           'age': row[1]['age'],'overall_survival': row[1]['overall_survival_in_days'],'current_treatment': row[1]['current_treatment']}
            for col in df.filter(regex='gene_').columns:
                new_row_tdf[col] = row[1][col]
            transf_dataset.append(new_row_tdf)
            if args.verbose > 1:
                print(f"New row {new_row_tdf['patient_id']} {new_row_tdf['status']} {new_row_tdf['tnum']} {new_row_tdf['treatment_time']} {new_row_tdf['disease_free_time']} {new_row_tdf['response']} ")
    if args.verbose > 0:
        print(f"Number of patients with missed time of treatment: {len(list_of_lost_times.keys())}")
        print(f"Number of patients with missed information about treatment and response types: {len(list_of_lost_repsonse_treatment.keys())}")

    if args.verbose > 1:
        print(f"List of patients with missed time of treatment :\n {list_of_lost_times}")
        print(f"List of patients with missed information about treatment and response type :\n {list_of_lost_repsonse_treatment}")



    tdf = pd.DataFrame(transf_dataset)
    # remove rows with NaN in response or treatment_type
    #tdf = tdf.dropna(subset=['response', 'treatment_type','disease_free_time'])
    tdf = tdf[tdf['disease_free_time'] >= 0]
    # if response is cntains string values replace with int(2)
    tdf['response_tmp'] = tdf['response'].apply(lambda x: 2 if isinstance(x, str) else x)
    # response is NaN set to 2
    tdf['response_tmp'] = tdf['response_tmp'].fillna(2)
    tdf['binary_response'] = tdf.apply(
        lambda x: 1 if x['response'] < 2.0 or (x['response'] == 2.0 and x['disease_free_time'] < 180) else 0, axis=1)
    #in group by patient_id set status to 0 for all tnum < max(tnum) for this patient_id
    tdf['maxtnum'] = tdf.groupby('patient_id')['tnum'].transform('max')
    tdf['status'] = tdf.apply(lambda x: 1 if x['tnum'] < x['maxtnum'] else x['status'], axis=1)



    tdf.to_csv(args.output_csv, index=False)
