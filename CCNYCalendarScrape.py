# importing libraries 
import pandas as pd
import requests 
from bs4 import BeautifulSoup

url = 'https://www.ccny.cuny.edu/registrar/fall'
response = requests.get(url)