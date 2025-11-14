## DOS2UNIX launcher.sh
dos2unix ./launcher.sh
dos2unix ./app_runner_workflow_hmc_base_main.py
dos2unix ./app_runner_workflow_hmc_base.json
dos2unix ./requirements.sh
dos2unix ./venvSetup.sh

docker build --no-cache --progress=plain -t cima-aircs/hmc-trainig:dev . 

docker save cima-aircs/hmc-trainig:dev  -o hmc-taining.tar