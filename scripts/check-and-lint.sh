# shellcheck disable=SC2046
poetry run black --check $(git ls-files '*.py')
poetry run mypy $(git ls-files '*.py')