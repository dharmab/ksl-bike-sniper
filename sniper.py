#!/usr/bin/env python3

from bs4 import BeautifulSoup
import logging
import os
import string
import sys
import urllib.parse
import urllib.request
import json


def __load_logger(name):
    """Configure a logger which logs to standard out"""
    new_logger = logging.getLogger(name)

    # Initial setup
    if not new_logger.handlers:
        # Add stdout handler
        stdout_handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        stdout_handler.setFormatter(formatter)
        new_logger.addHandler(stdout_handler)

        # Set logging level
        log_level_string = os.getenv('LOG_LEVEL')
        log_level_map = {
            'CRITICAL': logging.CRITICAL,
            'ERROR': logging.ERROR,
            'WARNING': logging.WARNING,
            'INFO': logging.INFO,
            'DEBUG': logging.DEBUG,
            'NOTSET': logging.NOTSET
        }
        if log_level_string not in log_level_map.keys():
            new_logger.warning('LOG_LEVEL not defined or not valid. Defaulting log level to WARNING')
        log_level = log_level_map.get(log_level_string, logging.WARNING)

        new_logger.setLevel(log_level)

    return new_logger

logger = __load_logger(__name__)

class Listing:
    listing_id = 0
    title = ''
    description = ''
    price = 0
    photo_link = ''

    @property
    def link(self):
        return 'https://www.ksl.com/classifieds/listing/' + str(self.listing_id)

    def to_json(self):
        properties = self.__dict__
        properties['link'] = self.link
        return json.dumps(properties)


def __query_recent_listings(min_price, max_price, zip_code, search_radius):
    base_url = 'https://www.ksl.com/classifieds/search/?'
    params = {
        'keyword': '',
        'category[]': 'Recreational Vehicles',
        'subCategory[]': 'Motorcycles, Road Bikes Used',
        'hasPhotos[]': 'Has Photos',
        'priceFrom': __int_to_price(min_price),
        'priceTo': __int_to_price(max_price),
        'postedTimeFQ[]': '1DAY',
        'city': '',
        'state': '',
        'zip': zip_code,
        'miles': search_radius,
        'sort': 0,
    }

    url = base_url + urllib.parse.urlencode(params)
    # Spoof as Chrome to avoid anti-bot measures
    headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'}
    request = urllib.request.Request(url=url, headers=headers)
    raw_html = urllib.request.urlopen(request).read()

    raw_soup = BeautifulSoup(raw_html, 'html.parser')
    listings_html = raw_soup.find_all('div', class_='listing')

    listings=[]
    for html in listings_html:
        # Skip ads
        if html.find(class_='featured'):
            continue

        new_listing = Listing()
        new_listing.listing_id = html['data-item-id']
        new_listing.title = html.find(class_='title').find('a').next.strip()
        new_listing.price = __price_to_int(html.find(class_='price').next.strip())
        new_listing.description = html.find(class_='description-text').next.strip()
        new_listing.photo_link = __parse_photo_link(html.find(class_='photo').find('a').find('img')['src'])
        listings.append(new_listing)
    return listings


def __parse_photo_link(raw_link):
    """Turn a listing's partial photo link into a full link"""
    # Remove everything after the last '?' to get the full resolution link
    return 'https:' + raw_link.rsplit('?', 1)[0]


def __int_to_price(price):
    return '$' + '{:,}'.format(price)


def __price_to_int(price):
    print(price)
    return int(price.rsplit('.', 1)[0].lstrip('$').replace(',', ''))


def __getenv(var, default):
    """os.getenv wrapper that also handles empty strings"""
    env = os.getenv(var)
    if env == "" or env is None:
        return default


def main():
    min_price = int(__getenv('MIN_PRICE', default='1000'))  # $1k
    max_price = int(__getenv('MAX_PRICE', default='100000'))  # $100k
    zip_code = __getenv('ZIP_CODE', default='84102')  # Temple Square
    search_radius = int(__getenv('SEARCH_RADIUS', default='100'))  # 100 miles

    logger.debug("Price range: {} to {}".format(min_price, max_price))
    logger.debug("Search area: {} miles around {}".format(search_radius, zip_code))
    listings = __query_recent_listings(
        min_price=min_price,
        max_price=max_price,
        zip_code=zip_code,
        search_radius=search_radius
    )

    for listing in listings:
        logger.debug(listing.to_json())

if __name__ == '__main__':
    main()
