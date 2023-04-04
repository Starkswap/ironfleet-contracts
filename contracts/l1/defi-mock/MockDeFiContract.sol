/**
    Mock DeFi contract.

    Allows two operations:
    1. Deposit input token to receive output token (deposit)
    2. Withdraw input token by sending output token (withdraw)

    The ratio for the input/output tokens swapped is 1-to-1 (adjusted for decimals).

    For example, 1 USDC (6 decimals) would be swapped for 1 WBTC (8 decimals).
    
    Therefore, if we only talk in terms of base units, 100 WBTC-base-units would be swapped for 1 USDC-base-units.
 */

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "./IGenericContract.sol";

// SPDX-License-Identifier: Apache-2.0.
pragma solidity ^0.6.12;

contract MockDeFiContract is IGenericContract {

    ERC20 public inputToken;
    ERC20 public outputToken;

    constructor(
        ERC20 _inputToken,
        ERC20 _outputToken
    ) public {
        inputToken = _inputToken;
        outputToken = _outputToken;
    }

    function withdraw(uint256 outputTokenAmount) external override {
        uint256 inputTokenAmountToSend = outputTokenAmount * 10 ** (inputToken.decimals() - outputToken.decimals());

        bool success = outputToken.transferFrom(msg.sender, address(this), outputTokenAmount);
        require(success, "Error transferring output token");

        success = inputToken.transfer(msg.sender, inputTokenAmountToSend);
        require(success, "Error transferring input token");
    }

    function deposit(uint256 inputTokenAmount) external override {
        uint256 outputTokenAmountToSend = inputTokenAmount * 10 ** (outputToken.decimals() - inputToken.decimals());

        bool success = inputToken.transferFrom(msg.sender, address(this), inputTokenAmount);
        require(success, "Error transferring input token");

        success = outputToken.transfer(msg.sender, outputTokenAmountToSend);
        require(success, "Error transferring output token");
    }
}
