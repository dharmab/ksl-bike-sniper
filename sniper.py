#!/usr/bin/env python3

from bs4 import BeautifulSoup
import boto3
import html
import json
import logging
import os
import pystache
import re
import sys
import urllib.parse
import urllib.request


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


def __sanitize_html_string(s):
    return html.unescape(s.strip())


def __query_recent_listings(min_price, max_price, zip_code, search_radius):
    logger.info('Querying KSL Classifieds')
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
    script = [s.get_text() for s in raw_soup.find_all('script') if "listings:" in s.get_text()][0]
    listings_json = re.search('listings:\s*(\[.*\])', script).group(1)
    listings = json.loads(listings_json)

    # Remove ads
    listings = [l for l in listings if l['listingType'] != 'featured']

    logger.debug('Found %d listings', len(listings))

    for listing in listings:
        listing['photo'] = 'https:' + listing['photo']

    return listings


def __int_to_price(price):
    return '$' + '{:,}'.format(price)


def __getenv(key, default=None):
    """os.getenv alternative that also handles empty strings"""
    value = os.getenv(key, None)
    if value == "" or value is None:
        return default
    return value


def __push_listings(listings):
    logger.debug('Accessing AWS resources')
    region = __getenv('AWS_REGION', 'us-west-2')
    sns = boto3.client('sns', region_name=region)
    dynamodb = boto3.resource('dynamodb', region_name=region)
    table = dynamodb.Table(__getenv('AWS_DYNAMODB_TABLE'))

    logger.info('Publishing listings')

    renderer = pystache.Renderer()

    published_counter = 0
    for listing in listings:
        listing_record = table.get_item(
            Key={'listing_id': listing['id']}
        ).get('Item', None)

        if not listing_record:
            subject = ''.join(renderer.render_path(
                'templates/subject.mustache',
                listing
            ).splitlines())[:99]
            message = renderer.render_path(
                'templates/listing.mustache',
                listing
            )
            print(subject)
            sns.publish(
                TopicArn=__getenv('AWS_SNS_TOPIC'),
                Subject=subject,
                Message=message
            )
            table.put_item(Item={'listing_id': listing['id']})
            published_counter += 1
            logger.debug(listing)
    if published_counter > 0:
        logger.info("Published {} listings".format(published_counter))
    else:
        logger.info("No new listings to publish!")


def __filter_listings(listings, included_terms=[], excluded_terms=[]):
    logger.info('Filtering listings for search terms')
    if included_terms:
        listings = [l for l in listings if any(term.lower() in (l['title'] + l['description']).lower() for term in included_terms)]

    if excluded_terms:
        listings = [l for l in listings if all(term.lower() not in (l['title'] + l['description']).lower() for term in excluded_terms)]

    return listings


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

    included_terms = __getenv('INCLUDED_SEARCH_TERMS')
    if included_terms:
        included_terms = included_terms.split(',')
    excluded_terms = __getenv('EXCLUDED_SEARCH_TERMS')
    if excluded_terms:
        excluded_terms = excluded_terms.split(',')

    listings = __filter_listings(
        listings=listings,
        included_terms=included_terms,
        excluded_terms=excluded_terms
    )

    __push_listings(listings)


if __name__ == '__main__':
    main()
