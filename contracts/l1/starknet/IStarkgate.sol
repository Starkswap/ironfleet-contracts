// SPDX-License-Identifier: Apache-2.0.
pragma solidity ^0.6.12;

interface IStarkgate {
    // Used for ETH deposits
    function deposit(uint256 l2Recipient) external;
    // Used for ERC20 deposits
    function deposit(uint256 amount, uint256 l2Recipient) external;
    function withdraw(uint256 amount, address recipient) external;
}
