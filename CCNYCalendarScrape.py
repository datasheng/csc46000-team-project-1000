# importing libraries 
import html
import pandas as pd
import requests 
from bs4 import BeautifulSoup

# specify URL, package request, send it and catch response
url = 'https://www.ccny.cuny.edu/registrar/fall'
r = requests.get(url)

# extract response as html
html.doc = r.text

# creating a Beautiful Soup Object 
soup = BeautifulSoup(html.doc, "html.parser")

# finding table
table = soup.find("table")

# creating data
data = []

# getting rid of headers
headers = [header.get_text(strip=True) for header in table.find('thead').find_all('th')]

# iterate through table rows
for row in table.find_all('tr'):
    cols = row.find_all('td')
    cols = [ele.text.strip() for ele in cols]
    data.append(cols)

# create dataframe
df = pd.DataFrame(data, columns=['DATE', 'DOW', 'TEXT'])

print(df.head)

# changing dates to python dates

df['DATE'] = pd.to_datetime('2021 ' + df['DATE'], format='%Y %B %d', errors='coerce').dt.strftime('%Y-%m-%d')

# first row has nothing in it, so getting rid of it
df = df.iloc[1:].reset_index(drop=True)
print(df.head())