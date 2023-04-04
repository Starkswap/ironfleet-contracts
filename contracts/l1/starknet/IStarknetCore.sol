/**
    File generated using https://bia.is/tools/abi2solidity/ on contract https://etherscan.io/address/0x944960b90381d76368aece61f269bd99fffd627e
    (proxied by https://etherscan.io/address/0xc662c410C0ECf747543f5bA90660f6ABeBD9C8c4).

    Interface of Starknet Core contract.
 */

// SPDX-License-Identifier: Apache-2.0.
pragma solidity ^0.6.12;

interface IStarknetCore {
  function consumeMessageFromL2 ( uint256 from_address, uint256[] calldata payload ) external returns ( bytes32 );
  // function finalize (  ) external;
  // function identify (  ) external pure returns ( string calldata );
  // function initialize ( bytes calldata data ) external;
  // function isFinalized (  ) external view returns ( bool );
  // function isFrozen (  ) external view returns ( bool );
  // function isOperator ( address testedOperator ) external view returns ( bool );
  // function l1ToL2MessageNonce (  ) external view returns ( uint256 );
  // function l1ToL2Messages ( bytes32 msgHash ) external view returns ( uint256 );
  // function l2ToL1Messages ( bytes32 msgHash ) external view returns ( uint256 );
  // function programHash (  ) external view returns ( uint256 );
  // function registerOperator ( address newOperator ) external;
  function sendMessageToL2 ( uint256 to_address, uint256 selector, uint256[] calldata payload ) external returns ( bytes32 );
  // function setProgramHash ( uint256 newProgramHash ) external;
  // function starknetAcceptGovernance (  ) external;
  // function starknetCancelNomination (  ) external;
  // function starknetIsGovernor ( address testGovernor ) external view returns ( bool );
  // function starknetNominateNewGovernor ( address newGovernor ) external;
  // function starknetRemoveGovernor ( address governorForRemoval ) external;
  // function stateBlockNumber (  ) external view returns ( int256 );
  // function stateRoot (  ) external view returns ( uint256 );
  // function unregisterOperator ( address removedOperator ) external;
  // function updateState ( uint256[] calldata programOutput, uint256 onchainDataHash, uint256 onchainDataSize ) external;
}
