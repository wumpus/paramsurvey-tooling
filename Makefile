.PHONY: unit unit_coverage unit_coverage_verbose integration integration_coverage integration_coverage_verbose clean_coverage test test_coverage test_coverage_verbose check_action distclean distcheck dist

unit:
	# hint: PYTEST_STDERR_VISIBLE=-s
	PYTHONPATH=. pytest tests/unit ${PYTEST_STDERR_VISIBLE}

unit_coverage:
	PYTHONPATH=. pytest --cov-append --cov-branch --cov paramsurvey_tooling tests/unit

unit_coverage_verbose:
	PYTHONPATH=. pytest --cov-append --cov-branch --cov paramsurvey_tooling -v -v tests/unit ${PYTEST_STDERR_VISIBLE}

integration:
	# hint: PYTEST_STDERR_VISIBLE=-s
	echo "initial ray stop, in case of previous strays"
	ray stop
	PYTHONPATH=. pytest --full-trace tests/integration ${PYTEST_STDERR_VISIBLE}

integration_coverage:
	echo "initial ray stop, in case of previous strays"
	ray stop
	PYTHONPATH=. pytest --cov-append --cov-branch --cov paramsurvey_tooling tests/integration ${PYTEST_STDERR_VISIBLE}

integration_coverage_verbose:
	echo "initial ray stop, in case of previous strays"
	ray stop
	PYTHONPATH=. pytest --cov-append --cov-branch --cov paramsurvey_tooling -v -v tests/integration ${PYTEST_STDERR_VISIBLE}

clean_coverage:
	rm -f .coverage

test: unit integration

test_coverage: clean_coverage unit_coverage integration_coverage

test_coverage_verbose: clean_coverage unit_coverage_verbose integration_coverage_verbose

check_action:
	python -c 'import yaml, sys; print(yaml.safe_load(sys.stdin))' < .github/workflows/test-all.yml > /dev/null

distclean:
	rm -rf dist/

distcheck: distclean
	python ./setup.py sdist
	twine check dist/*

dist: distclean
	echo "reminder, you must have tagged this commit or you'll end up failing"
	echo "  finish the CHANGELOG"
	echo "  git tag v0.x.x"
	echo "  git push --tags"
	python ./setup.py sdist
	twine check dist/*
	twine upload dist/* -r pypi
