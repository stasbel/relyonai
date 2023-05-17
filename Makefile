.PHONY: format lint test

format:
	# TODO: black isrot ...
	false

lint:
	# TODO: flake8 ...
	false

# there is no parallel option for tox config
# https://platform.openai.com/account/rate-limits 
# processes are 1 now as openai rate limits are tough
test:
	tox -p 0
