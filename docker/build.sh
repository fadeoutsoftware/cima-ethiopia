## DOS2UNIX launcher.sh
dos2unix ./launcher.sh
dos2unix ./app_runner_workflow_hmc_base_main.py
dos2unix ./app_runner_workflow_hmc_base.json
dos2unix ./requirements.sh
dos2unix ./venvSetup.sh

chmod +x launcher.sh
chmod +x requirements.sh
chmod +x venvSetup.sh

docker build --no-cache --progress=plain -t continuum-eth . 

docker save continuum-eth  -o continuum-eth.tar
