clean:
	rm -rf dist
build: clean
	python setup.py sdist bdist_wheel
release-test: build
	twine upload --repository-url https://test.pypi.org/legacy/ dist/*
release: build
	twine upload dist/*
