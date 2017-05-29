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
	-e LOG_LEVEL=$$LOG_LEVEL \
	$(PROJECT)
