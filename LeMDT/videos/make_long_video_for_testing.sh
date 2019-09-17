#! /bin/bash

ffmpeg -f concat -i mylist.txt -c copy video_draft.avi
