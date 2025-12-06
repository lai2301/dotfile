#!/bin/bash
# Script to display tasks in a floating terminal

cd "$(dirname "$0")"
go run tasks.go display

