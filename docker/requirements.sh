echo " ==================================================================================="
echo " ==> START ..."
echo " ==> Creating virual environment ..."

python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip

echo " ==> Installing requirements ..."
python3 -m pip install -r requirements_aics_iwrm.txt

echo " ==> Configuring Jupyter Lab ..."

jupyter nbextension install --py widgetsnbextension --sys-prefix \
 && jupyter nbextension enable --py widgetsnbextension --sys-prefix

echo " ==> DONE - Bye Bye"
echo " ==================================================================================="
