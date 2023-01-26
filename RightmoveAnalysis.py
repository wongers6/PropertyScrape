import os
import sys
from rightmove_webscraper import RightmoveData
from re import search
import pandas as pd
import requests
from lxml import html
import json
sys.path.append(os.path.dirname(os.getcwd()))

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
    else:
        return 'Undetermined'


def get_locationIdentifier(location):

    if any(char.isdigit() for char in location):
        # Output the dataframe of postcode
        postcodelink = 'https://www.rightmove.co.uk/property-for-sale/search.html?' \
                       'searchLocation=%s' \
                       '&useLocationIdentifier=false' \
                       '&locationIdentifier=' \
                       '&buy=For+sale' % location
        tree = html.fromstring(requests.get(postcodelink).text)
        # xp_postcode = """//div[@class="touchsearch-searchcriteria-value"]/text()"""
        xp_outcode = """//*[@id="locationIdentifier"]/@value"""
        return tree.xpath(xp_outcode)[0]
    else:
        # Output the dataframe of location identifier for each input for best matches
        code_url = 'https://www.rightmove.co.uk/typeAhead/uknostreet/'
        count = 0
        for char in location:
            if count == 2:
                code_url += '/'
                count = 0

            code_url += char.upper()
            count += 1
        res = requests.get(code_url).json()
        json_object = json.loads(json.dumps(res, indent=2))
        return pd.DataFrame(json_object['typeAheadLocations'])


def get_rightmove_url(rentsale, locationidentifier, radius, minprice, maxprice, minbed, maxbed):
    if rentsale == 'rent':
        url = "https://www.rightmove.co.uk/property-to-rent/find.html?searchType=RENT" \
               "&locationIdentifier=%s" \
               "&insId=1" \
               "&radius=%s" \
               "&minPrice=%s" \
               "&maxPrice=%s" \
               "&minBedrooms=%s" \
               "&maxBedrooms=%s" \
               "&displayPropertyType=" \
               "&maxDaysSinceAdded=" \
               "&sortByPriceDescending=" \
               "&_includeLetAgreed=on" \
               "&primaryDisplayPropertyType=" \
               "&secondaryDisplayPropertyType=" \
               "&oldDisplayPropertyType=" \
               "&oldPrimaryDisplayPropertyType=" \
               "&letType=" \
               "&letFurnishType=" \
               "&houseFlatShare=off" % (locationidentifier, radius, minprice, maxprice, minbed, maxbed)
    else:
        url = "https://www.rightmove.co.uk/property-for-sale/find.html?searchType=SALE" \
               "&locationIdentifier=%s" \
               "&insId=1" \
               "&radius=%s" \
               "&minPrice=%s" \
               "&maxPrice=%s" \
               "&minBedrooms=%s" \
               "&maxBedrooms=%s" \
               "&displayPropertyType=" \
               "&maxDaysSinceAdded=" \
               "&_includeSSTC=on" \
               "&sortByPriceDescending=" \
               "&primaryDisplayPropertyType=" \
               "&secondaryDisplayPropertyType=" \
               "&oldDisplayPropertyType=" \
               "&oldPrimaryDisplayPropertyType=" \
               "&newHome=" \
               "&auction=false" % (locationidentifier, radius, minprice, maxprice, minbed, maxbed)
    return url


def get_rightmovedata(rentsale, locationidentifier, radius, minprice, maxprice, minbed, maxbed):

    if locationidentifier == '':
        return pd.DataFrame()

    url = get_rightmove_url(rentsale, locationidentifier, radius, minprice, maxprice, minbed, maxbed)

    if rentsale == 'rent':
        # Scrape rental data from Rightmove:
        output = RightmoveData(url).get_results
        output['Rentsale'] = 'Rent'
        output['Category'] = output['type'].apply(lambda x: get_category(x))
        output['SearchTerm'] = locationidentifier
    else:
        # Scrape sales data from Rightmove
        output = RightmoveData(url).get_results
        output['Rentsale'] = 'Sale'
        output['Category'] = output['type'].apply(lambda x: get_category(x))
        output['SearchTerm'] = locationidentifier

    output = output.dropna(subset=['price'])
    output['Source'] = "Rightmove"

    return output