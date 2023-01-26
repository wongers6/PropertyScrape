import sys
sys.path.extend(['C:\\Users\\Simon\\PycharmProjects\\testing\\vene1'])
import pandas as pd
import numpy as np
import ZooplaAnalysis as ZA
from random import randint
from time import sleep, time
from datetime import datetime
import RightmoveAnalysis as RA


def Get_Property_Yield(city, radius_RENTAL, radius_SALE, minprice, maxprice, minbed, maxbed):

    # 1) Getting the zoopla sales result
    df_Zoopla = ZA.get_ZooplaData('sale', city, 'ALL', radius_SALE, minprice, maxprice, minbed, maxbed)
    df_Zoopla['Source'] = 'Zoopla'

    # 2) Getting the unique postcode to run for Rightmove sales
    postcode_list = df_Zoopla['postcode'].dropna().unique().tolist()

    # 3) Get unique postcode to run rental and rightmove sales data
    output = df_Zoopla
    rental = pd.DataFrame()
    for num, postcode in enumerate(postcode_list):
        sleep(randint(0, 2))
        print("Running data in..." + postcode + " Completed: " + str(int(100 * num / len(postcode_list))) + "%")

        # Zoopla rental
        df_Zoopla_Rent = ZA.get_ZooplaData('rent', postcode, 'ALL', radius_RENTAL, minprice, maxprice, minbed, maxbed)

        # Rightmove sales
        outcode = RA.get_locationIdentifier(postcode)
        df_Rightmove = RA.get_rightmovedata('sale', outcode, radius_SALE, minprice, maxprice, minbed, maxbed)
        output = pd.concat([output, df_Rightmove], sort=False)

        # Rightmove rental
        df_Rightmove_Rent = RA.get_rightmovedata('rent', outcode, radius_RENTAL, minprice, maxprice, minbed, maxbed)

        rental = pd.concat([rental, df_Zoopla_Rent, df_Rightmove_Rent])
        rental.reset_index(drop=True, inplace=True)

    output = output[output['Category'] != 'Undetermined']
    output['number_bedrooms'] = output['number_bedrooms'].apply(str)
    output.reset_index(drop=True, inplace=True)

    # 5) Applying rental info to sales dataframe
    rental_pvt = pd.pivot_table(rental,
                                values='price',
                                index=['postcode', 'Category', 'number_bedrooms'],
                                aggfunc=[np.mean,
                                         lambda x: len(x.unique()),
                                         np.std,
                                         np.median], dropna=False)

    output['est_rental'] = output.apply(lambda x: get_stats('yield', rental_pvt, x['postcode'], x['Category'],
                                                            x['number_bedrooms'], x['price']), axis=1)
    output['est_rental_1std'] = output.apply(lambda x: get_stats('yield_1std', rental_pvt, x['postcode'], x['Category'],
                                                                 x['number_bedrooms'], x['price']), axis=1)
    output['rental_count'] = output.apply(lambda x: get_stats('count', rental_pvt, x['postcode'], x['Category'],
                                                              x['number_bedrooms'], x['price']), axis=1)

    return rental, output


def get_stats(stats, rental_df, postcode, Category, no_bed, price):
    # no_bed = str(number_bedroom)
    # Category = str(Category)
    no_bed = str(no_bed)
    try:
        if stats == 'yield' and price != 0:
            return rental_df.loc[(postcode, Category, no_bed), ('mean', 'price')]*12/price
        if stats == 'yield_1std' and price != 0:
            rental_1std = rental_df.loc[(postcode, Category, no_bed), ('mean', 'price')] - \
                          rental_df.loc[(postcode, Category, no_bed), ('std', 'price')]
            return rental_1std*12/price
        elif stats == 'mean':
            return rental_df.loc[(postcode, Category, no_bed), ('mean', 'price')]
        elif stats == 'std':
            return rental_df.loc[(postcode, Category, no_bed), ('std', 'price')]
        elif stats == 'count':
            return rental_df.loc[(postcode, Category, no_bed), ('<lambda>', 'price')]
        elif stats == 'median':
            return rental_df.loc[(postcode, Category, no_bed), ('median', 'price')]
    except:
        return 0


# Looping through cities rental yield data
# CityInput = ['Manchester', 'Edinburgh', 'Newcastle', 'Peterborough', 'Hull',
#              'Portsmouth', 'Glasgow', 'Southend', 'Telford', 'Chelmsford',
#              'Norwich', 'Maidstone', 'York', 'Wigan', 'Coventry', 'Sheffield',
#              'Leicester', 'Birmingham', 'Leeds', 'Liverpool']

# CityInput = ['Edinburgh', 'Leeds', 'Sheffield', 'Glasgow']

CityInput = ['Portsmouth']

radius_RENTAL = 1
radius_SALE = 0
minprice = 0
maxprice = 1000000
minbed = 0
maxbed = 5

# 1) Create Dataframe for all locations for sales ======================================================================
output = pd.DataFrame()
rental = pd.DataFrame()
for city in CityInput:
    print("Running sales in..." + city)
    start = time()
    rental_single, output_single = Get_Property_Yield(city, radius_RENTAL, radius_SALE, minprice, maxprice, minbed, maxbed)
    print('Runtime took: ' + str(int(time() - start)) + 'sec')
    output = pd.concat([output, output_single])
    rental = pd.concat([rental, rental_single])
    output.to_csv("Property_Portsmouth" + datetime.today().strftime('%Y%m%d') + ".csv")
    rental.to_csv("Rental_Portsmouth" + datetime.today().strftime('%Y%m%d') + ".csv")

# file = 'C:\\Users\\Simon\\PycharmProjects\\testing\\vene1\\ZooplaData_20220213.xlsx'
# output = pd.read_excel(file, sheet_name='Sheet1', engine='openpyxl')
# Get rental and growth data for each property listing
# count = 0
# for url in output['url']:
#     output.loc[count, ['Est_Rental', 'Est_1y_ch', 'Est_5y_ch', 'Est_10y_ch']] = get_data_single_listing(url)
#     count += 1

# Example 2 - Get sales
# data_sale = get_ZooplaData('sale','Leeds', 'flats', 2, 100000)

# Example 3 - Get rental
# data_rent = get_ZooplaData('rent','Leeds', 'flats', 2, 100000)