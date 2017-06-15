.PHONY: default build

PROJECT = ksl-bike-sniper

default: build

build:
	docker build -t $(PROJECT) .

run: build
	docker run --rm -it \
	-e MIN_PRICE=$$MIN_PRICE \
	-e MAX_PRICE=$$MAX_PRICE \
	-e ZIP_CODE=$$ZIP_CODE \
	-e SEARCH_RADIUS=$$SEARCH_RADIUS \
	-e AWS_ACCESS_KEY_ID=$$AWS_ACCESS_KEY_ID \
	-e AWS_SECRET_ACCESS_KEY=$$AWS_SECRET_ACCESS_KEY \
	-e AWS_DYNAMODB_TABLE=$$AWS_DYNAMODB_TABLE \
	-e AWS_SNS_TOPIC=$$AWS_SNS_TOPIC \
	-e AWS_REGION=$$AWS_REGION \
	-e LOG_LEVEL=$$LOG_LEVEL \
	$(PROJECT)
