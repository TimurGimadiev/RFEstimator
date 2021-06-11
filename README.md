# Reaction Feasibility Estimator

Estimate reaction feasibility by difference in energy between energy of reactants and products

# Docker pull
    timurious/estimator:latest

# Docker build

To build an image:

    docker build . -t estimator 

# Input files
change directories in docker-compose file near to "source:" line, 
absolute path to dir with input.json should be provided. Example of json file is shown in example folder.

speed and precision of CREST calculations, possible options :

* crest_speed (https://github.com/grimme-lab/crest):
* * quick
* * squick 
* * mquick (default)
  
* dft:
* * priroda - use priroda16 for dft calculations (PBEPBE 3z),
              programm developed by D. Laikov https://rad.chem.msu.ru/~laikov/ru/
* * pyscf (not finished) - use pyscf package for calculations (B3LYP)
    None or not mentioned in json (default) - do not perform DFT

* obabel_fast - speed vs precision in 3D generation by openbabel (http://openbabel.org/wiki/Main_Page)
* * True - can save some time in generation of 3D by mmff94
* * False or not mentioned in json (default)

# Run calculations

    docker compose up
or

    docker stack deploy -c docker-compose.yaml estimator

The results will be stored in python .shelve file
For each job several types of responses available:
* ReactionComponents (python named tuple):
* * index - serial number of reaction
* * smi - SMILES of reaction
* * reactants - list of  CalcResult (python named tuple) for reactants
* * products - list of  CalcResult (python named tuple) for products
* * energy_dif - difference in energies between products and reactants (Hartree)
* * comments
* * time_s - calculation execution time
    
* CalcResult (python named tuple) - result of successful calculations
* * data - list of strings as lines in XYZ file
* * min_energy - energy of converged structure   
* * log - full output of calculations, if log option is None or omitted in json
    
* FailReport (python named tuple)
* * initial - initial file
* * log - output of calculations
* * step - at which step calculations failed

