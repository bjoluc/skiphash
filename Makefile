init:
	pipenv install

dev:
	pipenv install --dev

test:
	pipenv run py.test -v vaud

requirements:
	pipenv run pipenv_to_requirements
	cat requirements.txt | grep -v "#" >> requirements-dev.txt

.PHONY: init dev test requirements
