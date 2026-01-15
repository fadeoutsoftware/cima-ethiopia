#!/bin/bash -e
echo " ==================================================================================="
echo " ==> START ..."
echo " ==> Creating virual environment ..."

/usr/bin/python3.12 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip

echo " ==> Installing requirements ..."
python3 -m pip install -r requirements_aics_iwrm.txt

echo " ==> Configuring Jupyter Lab ..."

# jupyter labextension install --py widgetsnbextension \
# && jupyter labextension enable --py widgetsnbextension 

echo " ==> DONE - Bye Bye"
echo " ==================================================================================="
