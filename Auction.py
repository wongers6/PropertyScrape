import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re
from re import search
from datetime import datetime
import numpy as np
import requests
from bs4 import BeautifulSoup
import json
import warnings
# import ZooplaAnalysis as ZA

# Donwload driver here https://sites.google.com/chromium.org/driver/?pli=1
path = "C:\\Program Files (x86)\\chromedriver.exe"
driver = webdriver.Chrome(path)

def get_rent(link):

    driver.get(link)
    WebDriverWait(driver, 2).until(
        EC.element_to_be_clickable((By.XPATH,
                                    "//button[@class='_1cci9km0 _1cci9km4 _1gfrnkz8' and ./div/div/text()='See inside the estimate']"))).click()
    WebDriverWait(driver, 2).until(
        EC.element_to_be_clickable((By.XPATH,
                                    "//button[@aria-selected='false']"))).click()
    # Extract the rental and rental range
    rental_list = get_number(driver.find_elements(By.XPATH,"//p[@class='a5nzyx2 _1gfrnkz6']")[0].text)
    rent = np.mean(rental_list)
    rent_range = rental_list[1] - rental_list[0]

    return rent, rent_range

def get_rent_for_list(link_list):
    df = pd.DataFrame(columns=['rent', 'rent_range'])
    k = 0
    for link in link_list:
        try:
            rent, rent_range = get_rent('https://zoopla.co.uk/' + link)
        except:
            rent = None
            rent_range = None
        df.loc[k, 'rent'] = rent
        df.loc[k, 'rent_range'] = rent_range
        k += 1
    return df

def get_number(px_string):
    number1 = px_string.replace(',', '')
    number_list = re.findall(r'\d+', number1)
    number_list = list(map(float, number_list))
    if len(number_list) == 1:
        number_list = number_list[0]
    return number_list

def get_pricelevel(est_px_string):
    number_list = get_number(est_px_string)
    if len(number_list) == 2:
        px_range = float(number_list[1]) - float(number_list[0])
        est_px = 0.5*(float(number_list[0]) + float(number_list[1]))
        return px_range, est_px
    else:
        return 0, 0

def get_datetime(input):
    if input == '-':
        return None
    else:
        return datetime.strptime(input, ' - %b %Y')

def get_info_from_str(text_str):

    address = text_str[0]
    try:
        housenumber = int(re.findall(r"\d+", address)[0])
    except:
        housenumber = None
    try:
        EstPx_list = [float(i) for i in re.sub("[^0-9.\-]", "", text_str[-2]).split('-')]
        EstPx = np.mean(EstPx_list)
        EstPxRange = EstPx_list[1] - EstPx_list[0]
    except:
        EstPx = 0
        EstPxRange = 0

    bed = 0
    bath = 0
    reception = 0
    type = None
    other_type = None
    lastsold = None
    lastsoldpx = None
    index_type = None
    index_lastsold = None
    for index, i in enumerate(text_str):
        if search('bath',i):
            bath = int(i[0])
        elif search('bed',i):
            bed = int(i[0])
        elif search('reception',i):
            reception = int(i[0])
        elif i[-4:] == 'hold':
            type = i
            index_type = index
        elif i[:4] == 'Last':
            try:
                lastsold = datetime.strptime(i, 'Last sold - %b %Y')
            except:
                # For Sept!!!!
                try:
                    lastsold = datetime.strptime(i, 'Last sold - %bt %Y')
                except:
                    lastsold = None
            index_lastsold = index
            lastsoldpx = re.sub("[^0-9.\-]", "", text_str[index_lastsold + 1])

    if index_type is not None:
        other_type = '_'.join(text_str[index_type+1:index_lastsold])

    return address, housenumber, EstPx, EstPxRange, bed, bath, reception, type, other_type, lastsold, lastsoldpx

def get_allhouseprice(postcode):

    code_url = 'https://www.zoopla.co.uk/house-prices/?q=%s&search_source=house-prices' %(postcode.replace(' ',''))
    tree = requests.get(code_url).text
    soup = BeautifulSoup(tree, 'html.parser')
    # Find the number of results (if any)
    total_result = int(re.findall(r'\d+', soup.find('label', class_='mv5qvn0 _1gfrnkz8').text)[0])

    k = 0
    df = pd.DataFrame(columns=['link', 'address', 'housenumber', 'EstPx', 'EstPxRange',
                               'bed', 'bath', 'reception', 'type', 'other_type',
                               'lastsold', 'lastsoldpx'])
    if total_result != 0:
        # Get all links of the different pages
        link_list = [link['href']
                     for link in soup.find_all('a', attrs={'aria-live':'polite'})
                     if link.has_attr('href') and search('house-prices', link['href'])]
        link_list = set(link_list)

        for link in link_list:
            tree_link = requests.get('http://www.zoopla.co.uk' + link).text
            soup_link = BeautifulSoup(tree_link, 'html.parser')

            # Get all the listings on one page
            number_property = soup_link.find_all('a', class_='z96ijwa')
            for entry in number_property:
                property_str = entry.get_text("/")
                df.loc[k,['address', 'housenumber', 'EstPx', 'EstPxRange',
                          'bed', 'bath', 'reception', 'type', 'other_type',
                          'lastsold', 'lastsoldpx']] = get_info_from_str(property_str.split('/'))
                df.loc[k,'link'] = entry['href']
                # df.loc[k, ['EstRent','EstRentRange']] = get_rent('https://zoopla.co.uk/' + entry['href'])
                k += 1

    df['postcode'] = postcode
    df = df.sort_values(by=['housenumber'])

    return df

def NotNone(entry):
    try:
        return entry.text
    except:
        return None

def get_TaylorAuction_list(code_url):

    col_name = ['soldpx', 'address', 'postcode', 'house_no',
                'guidepx', 'des', 'no_bed', 'no_bath', 'no_reception']
    df = pd.DataFrame(columns=col_name)

    tree = requests.get(code_url).text
    soup = BeautifulSoup(tree, 'html.parser')
    total_result = soup.find_all('div', class_='col col-xs-12 col-sm-12 col-md-6 col-lg-6 col-xl-6 property-block')
    pat1 = r"\b([A-Za-z][A-Za-z]?[0-9][0-9]?[A-Za-z]?)\b"
    pat2 = r"\b([0-9][A-Za-z][A-Za-z])\b"

    k = 0
    for link in total_result:
        try:
            df.loc[k, 'soldpx'] = get_number(link.find('span', class_='property-status').text)
        except:
            try:
                df.loc[k, 'soldpx'] = link.find('span', class_='property-status').text
            except:
                df.loc[k, 'soldpx'] = None
        address = link.find('h3').text
        df.loc[k, 'address'] = address
        df.loc[k, 'postcode'] = re.search(pat1, address).group() + re.search(pat2, address).group()
        df.loc[k, 'house_no'] = int(re.findall(r"\d+", address)[0])
        df.loc[k, 'guidepx'] = get_number(link.find('span', class_='property-price').text)
        df.loc[k, 'des'] = NotNone(link.find('span', class_='feature'))
        df.loc[k, 'no_bed'] = NotNone(link.find('span',
                                                class_='property-detail-icon property-detail-icon-beds'))
        df.loc[k, 'no_bath'] = NotNone(link.find('span',
                                                 class_='property-detail-icon property-detail-icon-baths'))
        df.loc[k, 'no_reception'] = NotNone(link.find('span',
                                                      class_='property-detail-icon property-detail-icon-receptions'))

        k += 1

    return df

# Getting all housing data for a postcode =========================================================================
# code_url = 'https://www.taylorjamesauctions.co.uk/auction/tj-auction-venue-07-09-2022/'
# auction = get_TaylorAuction_list(code_url)
#
# for index, row in auction.iterrows():
#     print(row['address'])
#     zoopla_house = get_allhouseprice(row['postcode'])
#     selected = zoopla_house[zoopla_house['housenumber'].isin([row['house_no']])]
#     if not selected.empty:
#         auction.loc[index, 'EstPx'] = selected.iloc[0, selected.columns.get_loc("EstPx")]
#         auction.loc[index, 'EstPxRange'] = selected.iloc[0, selected.columns.get_loc("EstPxRange")]
#         link = 'https://zoopla.co.uk/' + selected.iloc[0, selected.columns.get_loc("link")]
#         auction.loc[index, 'ZLA_link'] = link
#     else:
#         auction.loc[index, 'EstPx'] = None
#         auction.loc[index, 'EstPxRange'] = None
#         auction.loc[index, 'ZLA_link'] = None

# selected = zoopla_house[zoopla_house['housenumber'].isin([2,4,6,8,10,12,14,16,18,20])]
# rent_data = get_rent_for_list(b['link'])
# =================================================================================================================

# list of postcode
# list_postcode = ["S739HT","S630QZ","DN58SA","S63OLJ","S645SN",
#                  "S630QQ","S636RE","S639ES","S639NW","S640HW",
#                  "S639LX","S649BT"]
#
# df = pd.DataFrame()
# for postcode in list_postcode:
#     df_temp = get_allhouseprice(postcode)
#     df = pd.concat([df, df_temp])

# List of link for rent
list_link = ["/property/uprn/100050755894/","/property/uprn/100050675282/",
             "/property/uprn/100050678304/","/property/uprn/100050826824/","/property/uprn/100050680685/",
             "/property/uprn/100050675858/","/property/uprn/100050682935/","/property/uprn/2007001126/",
             "/property/uprn/100050799408/","/property/uprn/100050810857/","/property/uprn/100050798152/",
             "/property/uprn/100050602361/"]

df_rentdata = get_rent_for_list(list_link)
