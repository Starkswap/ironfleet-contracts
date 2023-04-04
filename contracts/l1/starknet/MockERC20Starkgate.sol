// SPDX-License-Identifier: Apache-2.0.
pragma solidity ^0.6.12;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "./IStarkgate.sol";
import "./IStarknetMessaging.sol";

contract MockERC20Starkgate is IStarkgate {
    uint256 constant UINT256_PART_SIZE_BITS = 128;
    uint256 constant UINT256_PART_SIZE = 2**UINT256_PART_SIZE_BITS;

    IStarknetMessaging starknetCore;
    uint256 l2StarkgateAddress;
    ERC20 asset;

    event LogWithdrawal(address recipient, uint256 amount);

    constructor(
        IStarknetMessaging _starknetCore,
        uint256 _l2StarkgateAddress,
        ERC20 _asset
    ) public {
        starknetCore = _starknetCore;
        l2StarkgateAddress = _l2StarkgateAddress;
        asset = _asset;
    }

    function consumeMessage(uint256 amount, address recipient) internal {
        emit LogWithdrawal(recipient, amount);

        uint256[] memory payload = new uint256[](4);
        payload[0] = 0; // TRANSFER_FROM_STARKNET
        payload[1] = uint256(recipient);
        payload[2] = amount & (UINT256_PART_SIZE - 1);
        payload[3] = amount >> UINT256_PART_SIZE_BITS;

        starknetCore.consumeMessageFromL2(l2StarkgateAddress, payload);
    }

    // Used for ETH deposits
    function deposit(uint256 l2Recipient) override external {
        // Don't do anything.. we received the ETH as part of the tx
    }

    // Used for ERC20 deposits
    function deposit(uint256 amount, uint256 l2Recipient) override external {
        asset.transferFrom(msg.sender, address(this), amount);
    }

    function withdraw(uint256 amount, address recipient) override external {
        consumeMessage(amount, recipient);
        asset.transfer(recipient, amount);
    }
}
