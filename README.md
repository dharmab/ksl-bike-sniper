# KSL Bike Sniper

A script for parsing motorcycle listings on KSL.com, and forwarding interesting
ones to my email.

## Configuration

Configuration is set via environment variables.

- `MIN_PRICE`: The lowest price to search for, in USD. The default is `1000` ($1k).
- `MAX_PRICE`: The highest price to search for, in USD. The default is `100000` ($100k).
- `ZIP_CODE`: ZIP code where search will be centered. The default is `84102` (Temple Square, downtown Salt Lake City).
- `SEARCH_RADIUS`: Radius around ZIP code to search in miles. The default is `100` (100 miles).
- `AWS_ACCESS_KEY_ID`: Amazon Web Services access key.
- `AWS_SECRET_ACCESS_KEY`: Amazon Web Services secret key.
- `AWS_DYNAMODB_TABLE`: Existing DynamoDB table name in which listing status will be persisted. The primary partition key should be `listing_id`.
- `AWS_SNS_TOPIC`: Existing SNS topic ARN where listings will be forwarded.
- `AWS_REGION`: Name of AWS region containing DynamoDB table and SNS topic. The default is `'us-west-2'`.
- `INCLUDED_SEARCH_TERMS`: Comma-separated list of search terms. Only listings which include at least one search term will be forwarded. Terms are case-insensitive. Example: `'Honda,Kawasaki,Suzuki,Yamaha'`. This is not used unless defined.
- `EXCLUDED_SEARCH_TERMS`: Comma-separated list of search terms. Only listings which do not include any search term will be forwarded. Terms are case-insensitive. Example: `'Royal Enfield,scooter'`. This is not used unless defined.
- `LOG_LEVEL`: Logging verbosity. Set to `DEBUG` for development. The default is `WARN`.

## Build

You need Docker and Make.

`make build` will create a Docker container tagged `ksl-bike-sniper`.

## Run

`make run` will build and run a Docker container.

## Network and Security

### Ingress 

This application does accept any ingress connections.

### Egress

- `443/TCP HTTPS www.ksl.com`: Used to query recent classified listings.
- `443/TCP HTTPS <AWS Netblocks>`: Used to persist listing data in DynamoDB and send emails via SNS

## Changelog

### 1.0.0

First versioned release
