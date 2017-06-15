# KSL Bike Sniper

A script for parsing motorcycle listings on KSL.com

## Configuration

Configuration is set via environment variables.

- `MIN_PRICE`: The lowest price to search for, in USD. The default is `1000` ($1k).
- `MAX_PRICE`: The highest price to search for, in USD. The default is `100000` ($100k).
- `ZIP_CODE`: ZIP code where search will be centered. The default is `84102` (Temple Square, downtown Salt Lake City).
- `SEARCH_RADIUS`: Radius around ZIP code to search in miles. The default is `100` (100 miles).
- `AWS_ACCESS_KEY_ID`: Amazon Web Services access key.
- `AWS_SECRET_ACCESS_KEY`: Amazon Web Services secret key.
- `AWS_DYNAMODB_TABLE`: Existing DynamoDB table to persist listing status.
- `AWS_SNS_TOPIC`: Existing SNS topic ARN where listings will be forwarded.
- `AWS_REGION`: Name of AWS region containing DynamoDB table and SNS topic. The default is `'us-west-2'`.
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
