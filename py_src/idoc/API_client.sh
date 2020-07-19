#! /bin/bash
# This script runs several HTTP requests (GET and POST)
# to test the API of the IDOC client
sleep 5

# List available programs
curl localhost:80/device/be979e46217f3a5ec0f254245eb68da5/list_programs
sleep 1


# Load a program
echo '{"program_path": ["unittest_long.csv"]}' | curl -d @- localhost:80/device/be979e46217f3a5ec0f254245eb68da5/load_program
sleep 1

# Prepare the recognizer
curl localhost:80/device/be979e46217f3a5ec0f254245eb68da5/controls/recognizer/prepare
sleep 1

# Start the recognizer
curl localhost:80/device/be979e46217f3a5ec0f254245eb68da5/controls/recognizer/start
sleep 1

