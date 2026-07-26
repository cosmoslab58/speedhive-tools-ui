# Install virtual environment and dependencies (including test/lint tools)
install:
    python -m venv venv
    ./venv/bin/pip install --upgrade pip
    # Both pinned. Unpinned, CI linted against whatever ruff shipped that
    # week: 0.15 enabled 59 rules, 0.16 enabled 413, and a green build
    # turned into 312 errors in untouched code. lint rule selection is
    # now explicit in .ruff.toml too, so a bump is a deliberate act.
    ./venv/bin/pip install 'ruff==0.16.0' 'pytest==9.1.1'
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
