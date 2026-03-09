IMAGE_NAME := ringtail-python

.PHONY: build run deploy

build:
	docker build -t $(IMAGE_NAME) .

run: build
	docker run -p 8080:8080 $(IMAGE_NAME)

deploy:
	bl deploy
