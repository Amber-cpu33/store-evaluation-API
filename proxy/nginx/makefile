

all: build stop-container kill-container start ps


build:
	docker-compose build

stop-container:
	docker container stop nginx

kill-container:
	docker container rm nginx

start:
	docker-compose up -d

ps:
	docker ps