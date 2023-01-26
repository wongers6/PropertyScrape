import re
from re import search
import datetime as dt
import pandas as pd
import numpy as np
import requests
from lxml import html
from bs4 import BeautifulSoup
import json
import warnings
from cryptography.utils import CryptographyDeprecationWarning
warnings.filterwarnings("ignore", category=CryptographyDeprecationWarning)


def try_parse_date(text):
    # Convert the date from 1st Jun 2022 to datetime
    try:
        return dt.datetime.strptime(text, 'Listed on %dth %b %Y')
    except:
        try:
            return dt.datetime.strptime(text, 'Listed on %dnd %b %Y')
        except:
            try:
                return dt.datetime.strptime(text, 'Listed on %dst %b %Y')
            except:
                return dt.datetime.strptime(text, 'Listed on %drd %b %Y')


def price_to_number(string):
    # Convert the string to number format
    try:
        return float(re.sub("[^0-9.\-]", "", string))
    except:
        return 0


def get_category(string):
    # Get the category of the property
    if search('house', string):
        return 'House'
    elif search('apartment', string) or search('flat', string):
        return 'Flat'
    elif search('land', string):
        return 'Land'
    elif search('bungalow', string):
        return 'Bungalow'
    elif search('parking', string):
        return 'Parking'
    elif search('barn', string):
        return 'Barn Conversion'
    elif search('cottage', string):
        return 'Cottage'
    elif re.findall('Studio','rent Studio'):
        return 'Studio'
    elif search('room', string):
        return 'Room'
    else:
        return 'Undetermined'


def create_dataframe(tree):

    # Decide whether it is sale or rent
    if search('sale', tree.xpath("""//h1[@data-testid="results-title"]/text()""")[0]):
        Rentsale = 'sale'
    else:
        Rentsale = 'rent'

    # Creating the xpath expression for each entry
    xp_prices = """//p[@data-testid="listing-price"]/text()"""
    xp_des = """//h2[@data-testid="listing-title"]/text()"""
    xp_address = """//h3[@class="c-eFZDwI"]/text()"""
    xp_url = """//*[@class="c-hhFiFN"]/@href"""
    xp_agenturl = """//a[@data-testid="listing-details-agent-logo"]/@href"""
    xp_listedon = """//li[@class="c-eUGvCx"]/text()"""
    detail = tree.xpath("""//ul[@class='c-eahmek']/li/span/text()""")

    # Convert list of attributes to data table
    list_of_detail = np.reshape(detail, (int(len(detail)/2), 2))
    label = list()
    k = 0
    for x in list_of_detail[:, 0]:
        if x == 'Bedrooms':
            k += 1
        label.append(k)
    list_of_detail = np.hstack((list_of_detail, np.array(label).reshape(int(len(detail)/2), 1)))
    list_of_detail = pd.DataFrame(list_of_detail, columns=['attribute','Number','Property'])
    list_of_detail['Property'] = pd.to_numeric(list_of_detail['Property'])
    list_of_detail['Number'] = pd.to_numeric(list_of_detail['Number'])
    detail_df = pd.pivot_table(list_of_detail,
                       values='Number',
                       index=['Property'],
                       columns=['attribute'],
                       aggfunc=np.mean,
                       fill_value=0)

    # Extracting the data
    base = 'https://www.zoopla.co.uk'
    price_str = tree.xpath(xp_prices)
    price = [price_to_number(s.lstrip("£")) for s in price_str]
    des = tree.xpath(xp_des)
    address = tree.xpath(xp_address)
    url = list(set(tree.xpath(xp_url)))
    listlink = [f"{base}{url[w]}"
                for w in range(len(url))]
    agentlink = [f"{base}{tree.xpath(xp_agenturl)[w]}"
                 for w in range(len(tree.xpath(xp_agenturl)))]
    listedon = [try_parse_date(item)
                for item in tree.xpath(xp_listedon) if item[:9] != 'Available']

    # Get the postcode from address
    pat = r"\b([A-Za-z][A-Za-z]?[0-9][0-9]?[A-Za-z]?)\b"
    postcode_str = [re.findall(pat, w.split(',')[-1])[0] for w in address]
    number_bedroom = detail_df['Bedrooms']

    data = [price, des, address, listlink, agentlink, listedon, postcode_str, number_bedroom]
    temp_df = pd.DataFrame(data)
    temp_df = temp_df.transpose()
    columns = ["price", "type", "address", "url", "agent_url", "listed_on", "postcode_str", "number_bedroom"]
    temp_df.columns = columns

    # Get the search timestamp
    temp_df["search_date"] = dt.datetime.today()
    # Get the rent or sale flag
    temp_df["Rentsale"] = Rentsale
    # Get the property type from type
    temp_df['Category'] = temp_df['type'].apply(lambda x: get_category(x))

    return temp_df


def get_data_single_listing(url_single):
    # Get information for sale listing re rental and price growth
    tree = requests.get(url_single).text
    soup = BeautifulSoup(tree, 'html.parser')
    res = soup.find('script', type="application/json")
    json_object = json.loads(res.contents[0])
    try:
        MktStat = json_object['props']['pageProps']['listingDetails']['marketStats']
        # dict_keys(['__typename', 'areaName', 'areaNameUri', 'askingPrices', 'historicalEstimates',
        # 'sales', 'recentSales', 'propertyTypeGroup'])
        Est_rental = MktStat['askingPrices']['toRent']['meanValue']
        Est_1y_ch = MktStat['historicalEstimates'][3]['pctChangeSince']
        Est_5y_ch = MktStat['historicalEstimates'][4]['pctChangeSince']
        Est_10y_ch = MktStat['historicalEstimates'][5]['pctChangeSince']
    except:
        Est_rental = 0
        Est_1y_ch = 0
        Est_5y_ch = 0
        Est_10y_ch = 0
    return Est_rental, Est_1y_ch, Est_5y_ch, Est_10y_ch


def get_url_from_name(name):
    # Output the url string on the first location match based on postcode
    code_url = 'https://www.zoopla.co.uk/ajax/search/geo_autocomplete/?prev_search_term=%s&geo_search_term=%s&search_type=listings' %(name.lower(), name.lower())
    res = requests.get(code_url).json()
    json_object = json.loads(json.dumps(res, indent=2))
    return json_object['g'][0]['i']


def create_Zoopla_sale_url(location, category, radius, minprice, maxprice, minbed, maxbed):

    base_url = 'https://www.zoopla.co.uk/for-sale/'

    # Can be one of three: house, flat or property
    if category == 'flats' or category == 'houses':
        base_url = base_url + category + '/'
    else:
        base_url = base_url + 'property/'

    # Get the location
    if any(char.isdigit() for char in location):
        # The location is a postcode
        base_url = base_url + location + '/'
    else:
        # The location is a name
        base_url = base_url + get_url_from_name(location) + '/'

    # Additional filters
    base_url = base_url + '?results_sort=newest_listings'
    if maxbed > 0:
        base_url = base_url + '&beds_max=' + str(maxbed)
    if minbed > 0:
        base_url = base_url + '&beds_min=' + str(minbed)
    if maxprice > 0:
        base_url = base_url + '&price_max=' + str(maxprice)
    if minprice > 0:
        base_url = base_url + '&price_min=' + str(minprice)
    if radius > 0:
        base_url = base_url + '&radius=' + str(radius)

    return base_url


def create_Zoopla_rent_url(location, category, radius, minprice, maxprice, minbed, maxbed):

    base_url = 'https://www.zoopla.co.uk/to-rent/'

    # Can be one of three: house, flat or property
    if category == 'flats' or category == 'houses':
        base_url = base_url + category + '/'
    else:
        base_url = base_url + 'property/'

    # Get the location
    if any(char.isdigit() for char in location):
        # The location is a postcode
        base_url = base_url + location.replace(' ','-') + '/'
    else:
        # The location is a name
        base_url = base_url + get_url_from_name(location) + '/'

    # Additional filters
    base_url = base_url + '?results_sort=newest_listings'
    # Get rental per month
    base_url = base_url + '&price_frequency=per_month'

    if maxbed > 0:
        base_url = base_url + '&beds_max=' + str(maxbed)
    if minbed > 0:
        base_url = base_url + '&beds_min=' + str(minbed)
    if maxprice > 0:
        base_url = base_url + '&price_max=' + str(maxprice)
    if minprice > 0:
        base_url = base_url + '&price_min=' + str(minprice)
    if radius > 0:
        base_url = base_url + '&radius=' + str(radius)

    return base_url


def get_ZooplaData(Rentsale, location, category, radius, minprice, maxprice, minbed, maxbed):
    if Rentsale == 'rent':
        url = create_Zoopla_rent_url(location, category, radius, minprice, maxprice, minbed, maxbed)
    else:
        url = create_Zoopla_sale_url(location, category, radius, minprice, maxprice, minbed, maxbed)

    tree = html.fromstring(requests.get(url).text)
    xp_result = """//p[@data-testid="total-results"]/text()"""

    # Find the number of results (if any)
    try:
        total_result = re.findall(r'\d+', tree.xpath(xp_result)[0])

        # First page result
        df = create_dataframe(tree)

        # Loop through subsequent page results
        for p in range(2, int(float(total_result[0]) / 25) + 2):
            # Create the URL of the specific results page:
            p_url = url + "&pn=" + str(p)
            temp_tree = html.fromstring(requests.get(p_url).text)
            temp_df = create_dataframe(temp_tree)
            df = pd.concat([df, temp_df])

        df['SearchTerm'] = location
        df['Source'] = 'Zoopla'
        df = df.dropna(subset=['price'])
        df = df.reset_index(drop=True)

    except:

        #NO RESULT
        df = pd.DataFrame()

    return df

# radius_RENTAL = 1
# radius_SALE = 0
# create_Zoopla_sale_url('NR32 1SA', 'ALL', 1, 0, 250000, 2, 2)

# houses or flats or ALL
# radius_SALE = 3 # radius in miles
# minprice = 50000
# maxprice = 250000
# minbed = 0
# maxbed = 2
# df_Zoopla_Rent = get_ZooplaData('rent', 'SE19 3TW', 'ALL', 3, 0, 20000, 0, 3)
# df_Zoopla_Sale = get_ZooplaData('sale', 'SE19 3TW', 'ALL', radius_SALE, minprice, maxprice, minbed, maxbed)
