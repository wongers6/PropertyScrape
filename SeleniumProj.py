import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re
import numpy as np

def get_number(px_string):
    number1 = px_string.replace(',', '')
    number_list = re.findall(r'\d+', number1)
    number_list = list(map(float, number_list))
    if len(number_list) == 1:
        number_list = number_list[0]
    return number_list

def get_rent(link):

    driver.get(link)
    WebDriverWait(driver, 2).until(
        EC.element_to_be_clickable((By.XPATH,
                                    "//button[@class='c-klmMZv c-klmMZv-hcwTTk-category-tertiary']"))).click()
    WebDriverWait(driver, 2).until(
        EC.element_to_be_clickable((By.XPATH,
                                    "//button[@aria-selected='false']"))).click()
    # Extract the rental and rental range
    rental_list = get_number(driver.find_elements(By.CLASS_NAME,'c-dEtqoh')[0].text)
    rent = np.mean(rental_list)
    rent_range = rental_list[1] - rental_list[0]

    return rent, rent_range

# Donwload driver here https://sites.google.com/chromium.org/driver/?pli=1
path = "C:\\Program Files (x86)\\chromedriver.exe"
driver = webdriver.Chrome(path)

# links = ['https://www.zoopla.co.uk/property/uprn/100011467918/',
#         'https://www.zoopla.co.uk/property/uprn/100011467937/',
#         'https://www.zoopla.co.uk/property/uprn/100011467859/']

def get_rent_for_list(link_list):
    df = pd.DataFrame(columns=['rent', 'rent_range'])
    k = 0
    for link in link_list:
        rent, rent_range = get_rent(link)
        df.loc[k, 'rent'] = rent
        df.loc[k, 'rent_range'] = rent_range
    return df
