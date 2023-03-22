# shellcheck disable=SC2046
poetry run black $(git ls-files '*.py')
poetry run isort $(git ls-files '*.py')