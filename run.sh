#!/usr/bin/env bash
# Launch the Streamlit app with WeasyPrint's macOS dylib path set.
set -e
cd "$(dirname "$0")"
source .venv/bin/activate
export DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib:$DYLD_FALLBACK_LIBRARY_PATH
exec streamlit run app.py "$@"
