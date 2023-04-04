# Starkswap Ironfleet Contracts [![Ironfleet  CI](https://github.com/Starkswap/ironfleet-contracts/actions/workflows/CI.yml/badge.svg)](https://github.com/Starkswap/ironfleet-contracts/actions/workflows/CI.yml)

Contracts for the Starkswap Ironfleet 

# Development setup
This project uses hardhat with the starknet-hardhat plugin in conjunction with a local python venv

1. Clone the repo
1. `python -m venv venv && source venv/bin/activate && pip install -r requirements.txt && deactivate`
1. `yarn install`
1. `yarn compile`
1. `source venv/bin/activate && yarn test`


## Building and testing L1 contracts
Compile solidity by running:
`yarn compile:l1`

Run mocha tests by running
`yarn test:l1`

## Building and testing L2 contracts
Compile cairo by running:
`yarn compile:l2`

Run pytest suite by running (Make sure the venv is running)
`yarn test:l2`

### Pytest notes
Run all tests `pytest -s tests/l2/pytest` 
> Note that `-s` redirects test output to stdout to see some progress

Alternatively the tests can be run separately using commands similar to `pytest -s tests/l2/pytest/test_finalise.py::TestFinalizeInsufficientBalance`
which can be used to try running individual suites or parallelise the run by starting different files in separate shells

