.PHONY: docs diagrams site pdf all verify shell clean

docs:
	docker compose up --build docs

diagrams:
	docker compose run --rm --build diagrams

site:
	docker compose run --rm --build site

pdf:
	docker compose run --rm --build pdf

all:
	docker compose run --rm --build all

verify:
	docker compose run --rm --build verify

shell:
	docker compose run --rm --build shell

clean:
	rm -rf site build
