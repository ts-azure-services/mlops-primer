import math
import pandas as pd
import numpy as np
import uuid

def bin_column(df=None, new_col_name=None, base_col=None, number_bins=None):
    """Bin data for specific columns"""
    df[new_col_name] = pd.cut(x = df[base_col],bins=number_bins,include_lowest=True)
    return df

def round_logic(val=None):
    """Rounding logic for customer assignments"""
    frac, whole = math.modf(val)
    if frac < 0.5:
        ret_val = math.floor(val)
    else:
        ret_val = np.ceil(val)
    return ret_val

def integer_alignment(
        base_list=None,
        change_list=None,
        target=None,
        ):
    """Align float values to the targeted integer total"""
    # Get the sum of the base and the list to change
    base_list_sum=sum(base_list)
    change_list_sum=sum(change_list)

    # Compare against the target, and iterate
    if base_list_sum == target:
        pass
    elif base_list_sum < target:
        # Then +1, for each list item
        i = 0
        while change_list_sum != target:
            # Keep iterating through if you come to the end of the list
            if i > len(change_list) - 1:
                i = 0
            else:
                change_list[i] = change_list[i] + 1
                change_list_sum = sum(change_list)
                i += 1
    else:
        # Then -1, for each list item
        i = 0
        while change_list_sum != target:
            if i > len(change_list) - 1:
                i = 0
            else:
                change_list[i] = change_list[i] - 1
                change_list_sum = sum(change_list)
                i += 1
    #print(f'original list: {base_list}')
    #print(f'new list: {change_list}')
    #print(f'target: {target}')
    #print(f'sum of original list: {base_list_sum}')
    #print(f'sum of new list: {change_list_sum}')
    return base_list, change_list, base_list_sum, change_list_sum

df = pd.read_csv('./../datasets/input-data/WA_Fn-UseC_-Telco-Customer-Churn.csv')
#df['TotalCharges'] = df['TotalCharges'].str.replace(r' ','0').astype(float)
df['Churn'] = df['Churn'].apply(lambda x: 0 if x == "No" else 1)
df['SeniorCitizen'] = df['SeniorCitizen'].apply(lambda x: "No" if x == 0 else "Yes")

# Bin columns
df = bin_column(df=df, new_col_name='tenure_bins', base_col='tenure', number_bins=10)
df = bin_column(df=df, new_col_name='monthly_charges_bins', base_col='MonthlyCharges', number_bins=10)
df = df.drop(['TotalCharges', 'MonthlyCharges', 'tenure'], axis=1)
df['monthly_charges_bins'] = df['monthly_charges_bins'].astype(object)
df['tenure_bins'] = df['tenure_bins'].astype(object)


col_list = list(df.columns)
non_attribute_cols = ['customerID', 'MonthlyCharges', 'Churn']
attribute_cols = list( set(col_list) - set(non_attribute_cols) )

temp_df = df.groupby(by=attribute_cols).agg({
    'customerID':'count',
    'Churn':['sum']#,'count']
    })
temp_df.columns = ['original_customer_count', 'original_churn_sum']#, 'churn_count']

# Convert to new df
new_df = temp_df.reset_index()
new_df['original_churn_ratio'] = new_df['original_churn_sum'] / new_df['original_customer_count']
new_df['original_customer_ratio'] = new_df['original_customer_count'] / new_df['original_customer_count'].sum()
#new_df = new_df.drop(['customer_count', 'churn_sum'], axis=1)

# Distribute customer totals
new_vol = 6900
new_df['new_customer_count_float'] = new_df['original_customer_ratio'] * new_vol
new_df['new_customer_count_int'] = new_df.apply(lambda x: round_logic(x['new_customer_count_float']), axis=1)
# Sort to get the most volume for reconciling
new_df = new_df.sort_values(by='new_customer_count_int', ascending=False)

# After resolving to integers and sorting, then finetune to get to the right population size
cust_count_base_list = new_df['new_customer_count_int'].to_list()
change_list = cust_count_base_list.copy()

base_list, change_list, base_list_sum, change_list_sum =\
        integer_alignment(
        base_list=cust_count_base_list,
        change_list=change_list,
        target= new_vol,
        )

new_df['new_customer_optimized'] = change_list
# Convert to int, so it can be used in range functions
new_df['new_customer_optimized'] = new_df['new_customer_optimized'].astype(int)
new_df['new_churn_customers'] = new_df['new_customer_optimized'] * new_df['original_churn_ratio']
new_df['new_churn_customers'] = new_df.apply(lambda x: round_logic(x['new_churn_customers']), axis=1)

#print(new_df.info())
#new_df.to_csv('temp.csv', encoding='utf-8', index=False)

list_of_records = new_df.to_dict('records')
s1 = list_of_records[0:1]

temp_customer_list = []
# Iterate through the dictionary to produce rows
for dictionary in s1:
    for i in range(dictionary['new_customer_optimized']):
        # Provide the blueprint to create a distinct row
        temp_dict = dictionary
        temp_dict['customerID'] = str(uuid.uuid1())
        temp_customer_list.append(temp_dict)

    temp_df = pd.DataFrame(temp_customer_list)
    segment_churn_ratio = dictionary['original_churn_ratio']
    temp_df['Churn'] = np.random.choice([1,0], size=len(temp_df),
            p=(segment_churn_ratio, 1-segment_churn_ratio )
            )

final_df = pd.DataFrame()
final_df = final_df.append(temp_df)
final_df.to_csv('final_df.csv', encoding='utf-8')
