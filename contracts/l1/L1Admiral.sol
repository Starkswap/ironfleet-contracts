// SPDX-License-Identifier: Apache-2.0.
pragma solidity ^0.6.12;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "./starknet/IStarkgate.sol";
import "./starknet/IStarknetMessaging.sol";

contract L1Admiral {
    // Selector when sending message to L2 to call the `process_message_from_l1` func on the L2 Admiral
    uint256 constant PROCESS_MESSAGE_FROM_L1_SELECTOR = 816708063554545988512071046177985264005137018110515604108563152300587620475;
    uint256 constant UINT256_PART_SIZE_BITS = 128;
    uint256 constant UINT256_PART_SIZE = 2**UINT256_PART_SIZE_BITS;

    // Immutable var means it could only be set in the constructor
    IStarknetMessaging public immutable starknetCore;
    uint256 public immutable l2Admiral;
    IStarkgate public immutable inputTokenStarkgate;
    IStarkgate public immutable outputTokenStarkgate;
    ERC20 public inputToken;
    ERC20 public outputToken;
    address public immutable destContract;  // The contract that converts input to output
    bytes4 public immutable sighash;    // The sighash to call on the contract to convert input to output

    // Topic hash: 0xbf09f4e1f80a105e9300ab0f966ce073a6b8f1a1675b0c89d29bdbd2a650b447
    event SuccessfulAmountWithdrawal(uint256 amount);
    // Topic hash: 0xc5db756d9d048094aa5017266616378c86aa7ed91f1d596c3b714b548bbe4fe7
    event UnsuccessfulAmountWithdrawal(uint256 amount);

    event SuccessfulAmountMessageWithdrawal(uint256 amount);
    event UnsuccessfulAmountMessageWithdrawal(uint256 amount);

    constructor(
        IStarknetMessaging _starknetCore,
        uint256 _l2Admiral,
        IStarkgate _inputTokenStarkgate,
        IStarkgate _outputTokenStarkgate,
        ERC20 _inputToken,
        ERC20 _outputToken,
        address _destContract,
        bytes4 _sighash
    ) public {
        starknetCore = _starknetCore;
        l2Admiral = _l2Admiral;
        inputTokenStarkgate = _inputTokenStarkgate;
        outputTokenStarkgate = _outputTokenStarkgate;
        inputToken = _inputToken;
        outputToken = _outputToken;
        destContract = _destContract;
        sighash = _sighash;
    }

    /**
     * This function is triggered by the Keeper (or by a user) and executes all the rides.
     * 
     * If one of the rideAmounts given is not executable (i.e., the tokens haven't made it yet from L2 and we cannot
     * execute them), then this function will still execute the other rideAmounts.
     * 
     * The function returns an array of the rideAmounts which it successfully executed.
     */
    function executeRides(uint256[] calldata rideAmounts) external returns (uint256[] memory successfulRideAmounts) {
        uint256 startGas = gasleft();

        // Attempt to withdraw all rideAmounts from gate
        uint256 rideCount = rideAmounts.length;

        for(uint256 i = 0; i < rideCount; i++) {

            bool success = safeWithdrawFromGate(rideAmounts[i]);
            if (success) {
                emit SuccessfulAmountWithdrawal(rideAmounts[i]);
            } else {
                emit UnsuccessfulAmountWithdrawal(rideAmounts[i]);
            }
        }

        // Consume amount info message
        // The ones that we are able to consume (and have enough input token balance to actually execute) will be
        // pushed to successfulRideAmounts and their total to totalAmount
        uint256 inputTokenBalance = inputToken.balanceOf(address(this));
        uint256[] memory _successfulRideAmounts = new uint256[](rideCount);
        uint256 totalAmount = 0;
        uint256 successfulRideCount = 0;
        for(uint256 i = 0; i < rideCount; i++) {
            // If ride amount is bigger than our token balance, skip it
            if (rideAmounts[i] + totalAmount > inputTokenBalance) { continue; }

            // Consume the amount info message
            bool success = consumeAmountMessage(rideAmounts[i]);
            if (success) {
                totalAmount += rideAmounts[i];
                _successfulRideAmounts[successfulRideCount] = rideAmounts[i];
                successfulRideCount++;
                emit SuccessfulAmountMessageWithdrawal(rideAmounts[i]);
            } else {
                emit UnsuccessfulAmountMessageWithdrawal(rideAmounts[i]);
            }
        }

        // Return empty array if no rides were successfully withdrawn
        if (totalAmount == 0) return _successfulRideAmounts;

        // Swap
        uint256 outputTokenAmount = safeExecuteSwap(totalAmount);

        // Deposit to gate
        safeDepositToGate(outputTokenAmount);

        // Send message to L2 to finalize the ride
        // Construct the message's payload
        uint256[] memory payload = new uint256[](successfulRideCount * 2 + 5);
        payload[0] = successfulRideCount;
        // ride_amounts
        for(uint256 i = 0; i < successfulRideCount; i++) {
            // Convert uint256 to to low and high (in order to be receivable by L2)
            // low 128
            payload[i*2+1] = _successfulRideAmounts[i] & (UINT256_PART_SIZE - 1);
            // high 128
            payload[i*2+2] = _successfulRideAmounts[i] >> UINT256_PART_SIZE_BITS;
        }
        // total_payout
        payload[successfulRideCount * 2 + 1] = outputTokenAmount & (UINT256_PART_SIZE - 1);
        payload[successfulRideCount * 2 + 2] = outputTokenAmount >> UINT256_PART_SIZE_BITS;

        // gas_used
        // TODO: gas seems off.. it's weirdly unpredictable, for example:
        // goerli tx 0xa21612462039cafa68605a35b9e4520adf862defefb2f802608119fd862d095c:
        // gas reported by contract: 373888 - 71573 = 302315 // (71573 was added as an offset in the contract)
        // actual gas used: 287836
        // goerli tx 0x8c1002a37215c51e79a7255ddc5a52acec4e899e972f209a922295684e1e8890
        // gas reported by contract: 302312
        // actual gas used: 287681
        // could be a problem on goerli specifically (gasUsed() implementation is different than actual node implementation)?
        uint256 gasUsed = startGas - gasleft();
        payload[successfulRideCount * 2 + 3] = gasUsed & (UINT256_PART_SIZE - 1);
        payload[successfulRideCount * 2 + 4] = gasUsed >> UINT256_PART_SIZE_BITS;


        starknetCore.sendMessageToL2(
            l2Admiral,
            PROCESS_MESSAGE_FROM_L1_SELECTOR,
            payload
        );

        return _successfulRideAmounts;
    }

    /**
        Attempt to consume the amount message from the L2Conductor of the given amount.
        This function returns false if unsuccessful (e.g., message not available), and true if successful.
        It does not revert.
     */
    function consumeAmountMessage(uint256 amount) internal returns (bool success) {
        uint256[] memory payload = new uint256[](2);
        payload[0] = amount & (UINT256_PART_SIZE - 1);
        payload[1] = amount >> UINT256_PART_SIZE_BITS;

        try starknetCore.consumeMessageFromL2(l2Admiral, payload) returns (bytes32) {
            return true;
        } catch(bytes memory) {
            return false;
        }
    }

    /**
        Withdraw `amount` input token from the Stargate. Ensure that the correct amount was withdrawn.
        Returns true if successful in withdrawing given amount.
        Returns false if withdrawing function is unsucessful.
        Reverts if able to withdraw but wrong amount given from the gate.
     */
    function safeWithdrawFromGate(uint256 amount) internal returns (bool success) {
        uint256 inputTokenAmountBeforeWithdraw = inputToken.balanceOf(address(this));
        (bool _success,) = address(inputTokenStarkgate).call(abi.encodeWithSignature(
            "withdraw(uint256,address)",
            amount,
            address(this)
        ));
        if (!_success) {return false;}
        uint256 inputTokenAmountAfterWithdraw = inputToken.balanceOf(address(this));
        require(inputTokenAmountBeforeWithdraw + amount == inputTokenAmountAfterWithdraw, "Incorrect amount withdrawn from Starkgate");
        return true;
    }

    /**
        Deposit `amount` output token to the Starkgate. Ensure that the correct amount was deposited.
     */
    function safeDepositToGate(uint256 amount) internal {
        uint256 outputTokenAmountBeforeDeposit = outputToken.balanceOf(address(this));
        outputToken.approve(address(outputTokenStarkgate), amount);
        outputTokenStarkgate.deposit(amount, l2Admiral);
        uint256 outputTokenAmountAfterDeposit = outputToken.balanceOf(address(this));
        require(outputTokenAmountBeforeDeposit - amount == outputTokenAmountAfterDeposit, "Incorrect amount deposited to Starkgate");
    }

    /**
        Execute the func (denoted by sighash) on the contract that converts the input token to the output token.
        Return the amount of output token given.

        Checks:
        * This contract has enough input token
        * Correct amount of input token transferred
        * Output token was given to us

        Reverts if unsuccessful.
     */
    function safeExecuteSwap(uint256 amount) internal returns (uint256) {
        // Input/output token amount before
        uint256 inputTokenAmountBefore = inputToken.balanceOf(address(this));
        uint256 outputTokenAmountBefore = outputToken.balanceOf(address(this));

        // Checks
        require(inputTokenAmountBefore >= amount, "Not enough input token to execute swap.");

        // Approve token and do swap
        inputToken.approve(destContract, amount);
        bytes memory callData = abi.encodeWithSelector(
            sighash,
            amount
        );
        (bool _success,) = destContract.call(callData);
        require(_success, "Calling destination contract was unsuccessful.");

        // Input/output token amount after
        uint256 inputTokenAmountAfter = inputToken.balanceOf(address(this));
        uint256 outputTokenAmountAfter = outputToken.balanceOf(address(this));

        // Checks
        require(inputTokenAmountBefore - amount == inputTokenAmountAfter, "Incorrect amount of input token was transferred.");
        require(outputTokenAmountAfter > outputTokenAmountBefore, "No output token was transferred.");

        // Return output token amount given
        return outputTokenAmountAfter - outputTokenAmountBefore;
    }
}
