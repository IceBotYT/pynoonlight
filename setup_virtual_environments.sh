#!/bin/bash

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

echo "Please enter the path for your Python 3.7 executable:"
read python37

echo "Please enter the path for your Python 3.10 executable:"
read python310

echo "Creating virtual environments..."
echo ""
echo "-----"

virtualenv -p $python37 $SCRIPT_DIR/.3.7-venv
virtualenv -p $python310 $SCRIPT_DIR/.3.10-venv

echo "-----"
echo ""
echo "Installing dependencies in the Python 3.7 venv..."
echo ""
echo "-----"

source $SCRIPT_DIR/.3.7-venv/bin/activate
poetry install
deactivate

echo "-----"
echo ""
echo "Installing dependencies in the Python 3.10 venv..."
echo ""
echo "-----"

source $SCRIPT_DIR/.3.10-venv/bin/activate
poetry install
deactivate

echo "-----"
echo ""
echo "Adding activation aliases to ~/.bashrc"
echo "" >> ~/.bashrc
echo "alias noonlight_python3.10='source $SCRIPT_DIR/.3.10-venv/bin/activate'" >> ~/.bashrc
echo "alias noonlight_python3.7='source $SCRIPT_DIR/.3.7-venv/bin/activate'" >> ~/.bashrc
echo ""
echo "-----"
echo ""
echo "If there are no errors above, congratulations! The virtual environments have been created."
echo ""
echo "|"
echo "| To activate the Python 3.7 environment, type \"noonlight_python3.7\""
echo "|"
echo "| To activate the Python 3.10 environment, type \"noonlight_python3.10\""
echo "|"
echo "| To exit the environment, type \"deactivate\""
