# Install virtual environment and dependencies (including test/lint tools)
install:
    python -m venv venv
    ./venv/bin/pip install --upgrade pip
    # ruff is pinned: the recipe previously installed it unpinned, so CI
    # picked up whatever was current that day. 0.16.0 added rules that
    # produced 312 errors in untouched code and broke every PR, while
    # main had last gone green on 0.15.22. Bump deliberately, not by
    # accident of timing.
    ./venv/bin/pip install 'ruff==0.15.22' pytest
    ./venv/bin/pip install -r requirements.txt
    ./venv/bin/pip install -e ./speedhive-tools

# Run the test suite
test:
    ./venv/bin/pytest

# Run the lint checks
lint:
    ./venv/bin/ruff check --exclude venv --exclude speedhive-tools .

# Run the local Flask server
run:
    ./venv/bin/flask run --host=0.0.0.0 --port=8854

# Clean cache directories
clean:
    find . -type d -name "__pycache__" -exec rm -r {} +
    rm -rf .pytest_cache
