# KSL Bike Sniper

A script for parsing listings on KSL.com, and forwarding interesting ones to my
email. Originally used for used motorcycles, but has been expanded to allow
searching for most of the site.

## Configuration

Configuration is set via environment variables.

- `CATEGORY`: KSL listing category. The default is `Recreational Vehicles`.
- `SUBCATEGORY`: KSL listing subcategory. The default is `Motorcycles, Road Bikes Used`.
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
- `EXCLUDED_SEARCH_TERMS`: Comma-separated list of search terms. Only listings which do not include any search term will be forwarded. Terms are case-insensitive. Example: `'Hyosung,scooter'`. This is not used unless defined.
- `LOG_LEVEL`: Logging verbosity. Set to `DEBUG` for development. The default is `WARNING`.

## Build

You need Docker and Make.

`make build` will create a Docker container tagged `ksl-bike-sniper`.

## Run

`make run` will build and run a Docker container.

## Format

`make format` will autoformat the code.

## Test

There are no unit tests, but `make ci` will run code quality checks.

## Deploy

- Create a DynamoDB table with a primary key named `listing_id` of type Number. This table is used to track which KSL listings have been processed across runs. I also recommend lowering the provisioned read and write capacity to 1 and configuring `ttl` as the TTL attribute.
- Create an SNS topic and add your email as a subscription.
- Create an IAM policy:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "VisualEditor0",
            "Effect": "Allow",
            "Action": [
                "sns:Publish",
                "dynamodb:PutItem",
                "dynamodb:GetItem"
            ],
            "Resource": [
                "DynamoDB-Table-ARN",
                "SNS-Topic-ARN"
            ]
        }
    ]
}
```

- Bind the IAM policy to a role or user.
- Run as a scheduled job however you like. Systemd timer, [Kubernetes CronJob](deploy/kubernetes), ECS Fargate Scheduled Task, for loop in a screen session on some forgotten server...

## Network and Security

### Ingress 

This application does accept any ingress connections.

### Egress

- `443/TCP HTTPS www.ksl.com`: Used to query recent classified listings.
- `443/TCP HTTPS <AWS Netblocks>`: Used to persist listing data in DynamoDB and send emails via SNS
