# orca

Estimate reaction feasibility by difference in energy between energy of reactants and products

# Docker pull
timurious/estimator:latest

# Docker build

To buildand image:

    docker build . -t estimator 

# Docker run

Prepare env file with REDIS_URL key valued by redis task server url.
Run required amount of containers with next command:

      docker run -d --rm --env-file /path/to/env/file estimator
