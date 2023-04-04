import { HardhatUserConfig } from "hardhat/types";
import "@shardlabs/starknet-hardhat-plugin"
import "@nomiclabs/hardhat-waffle"


/**
 * @type import('hardhat/config').HardhatUserConfig
 */
const config: HardhatUserConfig = {
  networks: {
    devnet: {
      url: "http://localhost:5000"
    },
    hardhat: {
      forking: {
        // url: "https://mainnet.infura.io/v3/a3752ec06a7a4c64bfbe4de03e5a39fd"
        url: "https://goerli.infura.io/v3/49b0e120ae514f8f9a6d43b25ba398b3"
      }
    },
  },
  solidity: {
    version: "0.6.12"
  },
  paths: {
    tests: "./tests"
  },
  starknet: {
    network: "integrated-devnet",
    venv: "./venv"
  }
};

export default config;
