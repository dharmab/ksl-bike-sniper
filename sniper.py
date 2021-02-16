#!/usr/bin/env python3

from bs4 import BeautifulSoup
from typing import List, Optional
import boto3
import datetime
import html
import json
import logging
import os
import re
import sys
import urllib.parse
import urllib.request


def _getenv(key: str, default: Optional[str] = None) -> Optional[str]:
    "os.getenv alternative that also handles empty strings"
    value = os.getenv(key, None)
    if not value:
        value = default
    return value


def _load_logger(name: str) -> logging.Logger:
    "Configure a logger which logs to standard out"
    new_logger = logging.getLogger(name)

    # Initial setup
    if not new_logger.handlers:
        # Add stdout handler
        stdout_handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        stdout_handler.setFormatter(formatter)
        new_logger.addHandler(stdout_handler)

        # Set logging level
        log_level_string = _getenv("LOG_LEVEL", default="WARNING")
        assert log_level_string
        log_level_map = {
            "CRITICAL": logging.CRITICAL,
            "ERROR": logging.ERROR,
            "WARNING": logging.WARNING,
            "INFO": logging.INFO,
            "DEBUG": logging.DEBUG,
            "NOTSET": logging.NOTSET,
        }
        if log_level_string not in log_level_map.keys():
            new_logger.warning(
                "LOG_LEVEL not defined or not valid. Defaulting log level to WARNING"
            )
        log_level = log_level_map[log_level_string]

        new_logger.setLevel(log_level)

    return new_logger


logger = _load_logger(__name__)


def _sanitize_html_string(s: str) -> str:
    return html.unescape(s.strip())


def _query_recent_listings(
    category: str,
    subcategory: str,
    min_price: int,
    max_price: int,
    zip_code: str,
    search_radius: int,
) -> List[dict]:
    logger.info("Querying KSL Classifieds")
    base_url = "https://classifieds.ksl.com/search/?"
    params = {
        "keyword": "",
        "category[]": category,
        "subCategory[]": subcategory,
        "hasPhotos[]": "Has Photos",
        "priceFrom": _int_to_price(min_price),
        "priceTo": _int_to_price(max_price),
        "postedTimeFQ[]": "1DAY",
        "city": "",
        "state": "",
        "zip": zip_code,
        "miles": search_radius,
        "sort": 0,
    }

    url = base_url + urllib.parse.urlencode(params)
    # Spoof as Chrome to avoid anti-bot measures
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.135 Safari/537.36"
    }
    request = urllib.request.Request(url=url, headers=headers)
    raw_html = urllib.request.urlopen(request).read()

    raw_soup = BeautifulSoup(raw_html, "html.parser")
    script = [
        s.get_text() for s in raw_soup.find_all("script") if "listings:" in s.get_text()
    ][0]
    match = re.search(r"listings:\s*(\[.*\])", script)
    assert match
    listings = json.loads(match.group(1))

    # Remove ads
    listings = [l for l in listings if l["listingType"] != "featured"]

    logger.debug("Found %d listings", len(listings))

    # Sanitize content
    for listing in listings:
        listing["photo"] = "https:{}".format(listing["photo"])
        listing["link"] = "https://www.ksl.com/classifieds/listing/{}".format(
            listing["id"]
        )

    return listings


def _int_to_price(price: int) -> str:
    return "$" + "{:,}".format(price)


def _push_listings(listings: List[dict]) -> None:
    logger.debug("Accessing AWS resources")
    region = _getenv("AWS_REGION", "us-west-2")
    sns = boto3.client("sns", region_name=region)
    dynamodb = boto3.resource("dynamodb", region_name=region)
    table = dynamodb.Table(_getenv("AWS_DYNAMODB_TABLE"))
    ttl = int((datetime.datetime.now() + datetime.timedelta(days=21)).timestamp())

    logger.info("Publishing listings")

    published_counter = 0
    for listing in listings:
        listing_record = table.get_item(Key={"listing_id": listing["id"]}).get(
            "Item", None
        )

        if not listing_record:
            subject = "{} - ${}".format(listing["title"], listing["price"])[:99]

            logger.info(subject)
            logger.debug(listing)

            message = "\n".join(
                [listing["title"], "", listing["description"], "", listing["link"],]
            )

            sns.publish(
                TopicArn=_getenv("AWS_SNS_TOPIC"), Subject=subject, Message=message
            )
            table.put_item(Item={"listing_id": listing["id"], "ttl": ttl})

            published_counter += 1

    if published_counter > 0:
        logger.info(f"Published {published_counter} listings")
    else:
        logger.info("No new listings to publish!")


def _filter_listings(
    listings: List[dict],
    included_terms: Optional[List[str]] = None,
    excluded_terms: Optional[List[str]] = None,
) -> List[dict]:
    if included_terms is None:
        included_terms = []
    if excluded_terms is None:
        excluded_terms = []

    logger.info("Filtering listings for search terms")
    if included_terms:
        listings = [
            l
            for l in listings
            if any(
                term.lower() in (l["title"] + l["description"]).lower()
                for term in included_terms
            )
        ]

    if excluded_terms:
        listings = [
            l
            for l in listings
            if all(
                term.lower() not in (l["title"] + l["description"]).lower()
                for term in excluded_terms
            )
        ]

    return listings


def main() -> None:
    category = _getenv("CATEGORY", default="Recreational Vehicles")
    assert category
    subcategory = _getenv("SUBCATEGORY", default="Motorcycles, Road Bikes Used")
    assert subcategory
    min_price = _getenv("MIN_PRICE", default="1000")  # $1k
    assert min_price
    max_price = _getenv("MAX_PRICE", default="100000")  # $100k
    assert max_price
    zip_code = _getenv("ZIP_CODE", default="84102")  # Temple Square
    assert zip_code
    search_radius = _getenv("SEARCH_RADIUS", default="100")  # 100 miles
    assert search_radius

    logger.debug(f"Price range: {min_price} to {max_price}")
    logger.debug(f"Search area: {search_radius} miles around {zip_code}")

    listings = _query_recent_listings(
        category=category,
        subcategory=subcategory,
        min_price=int(min_price),
        max_price=int(max_price),
        zip_code=zip_code,
        search_radius=int(search_radius),
    )

    def term_list(var: str) -> Optional[List[str]]:
        terms = _getenv(var)
        return terms.split(",") if terms is not None else None

    listings = _filter_listings(
        listings=listings,
        included_terms=term_list("INCLUDED_SEARCH_TERMS"),
        excluded_terms=term_list("EXCLUDED_SEARCH_TERMS"),
    )

    _push_listings(listings)


if __name__ == "__main__":
    main()
