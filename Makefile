.PHONY: help install build deploy-site deploy-oauth deploy import clean

help:
	@echo "make install       - npm install"
	@echo "make build         - build the site"
	@echo "make deploy-site   - build + deploy the blog worker (ayunovanti)"
	@echo "make deploy-oauth  - deploy the CMS/giscus OAuth worker (blog-cms-auth)"
	@echo "make deploy        - deploy everything (site + oauth worker)"
	@echo "make import        - import all WordPress posts (skips already-imported)"
	@echo "make clean         - remove build artifacts"

install:
	npm install

build:
	npm run build

deploy-site: build
	npx wrangler deploy

deploy-oauth:
	cd oauth-worker && npx wrangler deploy -c wrangler.toml

deploy: deploy-site deploy-oauth

import:
	python3 scripts/import_wp_post.py --all

clean:
	rm -rf dist .astro
