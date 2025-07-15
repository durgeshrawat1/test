#!/bin/bash

INPUT_FILE="$1"
LOG_DIR="logs"
LOGFILE="$LOG_DIR/invocation_$(date +'%Y%m%d_%H%M%S').log"

# Check if input file is provided
if [ -z "$INPUT_FILE" ]; then
  echo "❌ Usage: ./run_distance.sh <input_filename>" | tee -a "$LOGFILE"
  exit 1
fi

# Create log directory if it doesn't exist
if [ ! -d "$LOG_DIR" ]; then
  echo "📁 Log directory '$LOG_DIR' does not exist. Creating it..."
  mkdir -p "$LOG_DIR"
fi

echo "🚀 Running distance script with file: $INPUT_FILE" | tee -a "$LOGFILE"

# Run python script and append output and errors to log file
python3 distance_matrix_polars_config.py "$INPUT_FILE" >> "$LOGFILE" 2>&1

EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
  echo "❌ Script failed with exit code $EXIT_CODE" | tee -a "$LOGFILE"
else
  echo "✅ Script completed successfully" | tee -a "$LOGFILE"
fi

exit $EXIT_CODE
