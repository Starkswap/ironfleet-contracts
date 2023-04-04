/**
    This is a mock StarkGate contract for testing.
 */

// SPDX-License-Identifier: Apache-2.0.
pragma solidity ^0.6.12;

import "./StarknetMessaging.sol";

contract MockStarknetCore is StarknetMessaging {
    /**
        Add an L2 to L1 message so that we could consume it (for testing).
     */
    function addL2ToL1Message(uint256 from_address, uint256 to_address, uint256[] calldata payload)
        external returns (bytes32)
    {
        bytes32 msgHash = keccak256(
            abi.encodePacked(from_address, to_address, payload.length, payload)
        );
        l2ToL1Messages()[msgHash] += 1;
        return msgHash;
    }
}
