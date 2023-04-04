/**
    Only needed in order to provide Ethernal with an interface for contracts that our L1 conductors may interact with.
 */


// SPDX-License-Identifier: Apache-2.0.
pragma solidity ^0.6.12;

abstract contract IGenericContract {
    function withdraw(uint256) external virtual;
    function deposit(uint256) external virtual;
}
