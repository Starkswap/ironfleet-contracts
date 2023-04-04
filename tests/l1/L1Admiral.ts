import { Contract, ContractFactory, Signer } from "ethers";

const { expect } = require("chai");
const { ethers } = require("hardhat");

const UINT256_PART_SIZE_BITS = 128n;
const UINT256_PART_SIZE = 2n**UINT256_PART_SIZE_BITS;

const INPUT_TOKEN_L2_STARKGATE_ADDRESS = "0x2222222222222222222222222222222222222220"
const OUTPUT_TOKEN_L2_STARKGATE_ADDRESS = "0x2222222222222222222222222222222222222221"
const INPUT_TO_OUTPUT_L2_CONDUCTOR_ADDRESS = "0x2222222222222222222222222222222222222222";
const OUTPUT_TO_INPUT_L2_CONDUCTOR_ADDRESS = "0x2222222222222222222222222222222222222223";

/**
 * Add a starkgate token withdrawal message for the given amount and add it to the StarknetCore contract.
 */
const createStarkateTokenWithdrawalMessage = async (
    mockStarknetCore: Contract,
    l2StarkgateAddress: string,
    l1StarkgateAddress: string,
    toAddress: string,
    amount: number
) => {
    let payload: bigint[] = [];
    payload[0] = 0n; // TRANSFER_FROM_STARKNET, see StarknetTokenBridge.sol
    payload[1] = BigInt(toAddress);
    payload[2] = BigInt(amount) & (UINT256_PART_SIZE - 1n);
    payload[3] = BigInt(amount) >> UINT256_PART_SIZE_BITS;

    await mockStarknetCore.addL2ToL1Message(
        BigInt(l2StarkgateAddress),
        BigInt(l1StarkgateAddress),
        payload
    );
};

describe("L1Admiral", function () {
    let keeper: Signer;

    // Tokens
    let ERC20Token: ContractFactory;
    let inputToken: Contract;
    let outputToken: Contract;

    // Starkgates
    let ERC20Starkgate: ContractFactory;
    let inputTokenStarkgate: Contract;
    let outputTokenStarkgate: Contract;

    // Starknet core
    let StarknetCore: ContractFactory;
    let starknetCore: Contract;

    // Target DeFi contract
    let DeFiContract: ContractFactory;
    let deFiContract: Contract;

    // L1Admiral
    let L1Admiral: ContractFactory;
    let l1Conductor: Contract;

    beforeEach(async function () {
        [keeper] = await ethers.getSigners()

        // ERC-20 tokens
        ERC20Token = await ethers.getContractFactory("MockERC20");
        inputToken = await ERC20Token.deploy("Input Token", "IN", 18);
        await inputToken.deployed();
        outputToken = await ERC20Token.deploy("Output Token", "OUT", 18);
        await outputToken.deployed();

        // Mock DeFi contract
        // (See contract file for explanation of how it works)
        DeFiContract = await ethers.getContractFactory("MockDeFiContract");
        deFiContract = await DeFiContract.deploy(inputToken.address, outputToken.address);
        await deFiContract.deployed();

        // Mock Starknet core
        StarknetCore = await ethers.getContractFactory("MockStarknetCore");
        starknetCore = await StarknetCore.deploy();

        // Mock Starkgates
        ERC20Starkgate = await ethers.getContractFactory("MockERC20Starkgate");
        inputTokenStarkgate = await ERC20Starkgate.deploy(
            starknetCore.address,
            INPUT_TOKEN_L2_STARKGATE_ADDRESS,
            inputToken.address
        );
        outputTokenStarkgate = await ERC20Starkgate.deploy(
            starknetCore.address,
            OUTPUT_TOKEN_L2_STARKGATE_ADDRESS,
            outputToken.address
        );

        // L1 conductor
        L1Admiral = await ethers.getContractFactory("L1Admiral");
        l1Conductor = await L1Admiral.deploy(
            starknetCore.address,
            INPUT_TO_OUTPUT_L2_CONDUCTOR_ADDRESS,
            inputTokenStarkgate.address,
            outputTokenStarkgate.address,
            inputToken.address,
            outputToken.address,
            deFiContract.address,
            "0xb6b55f25"
        );
        await l1Conductor.deployed();

        // Load contracts with tokens
        // DeFi contract with both input and output
        await inputToken.mint(deFiContract.address, 999999999999999);
        await outputToken.mint(deFiContract.address, 999999999999999);
        // Input token Starkgate with input token
        await inputToken.mint(inputTokenStarkgate.address, 999999999999999);

    });

    let rideAmounts = [
        [50],
        [1, 2, 3]
    ]

    rideAmounts.forEach(async function(amounts) {
        it("should execute rides", async function () {
            let totalAmounts = ethers.BigNumber.from(amounts.reduce((partialSum, a) => partialSum + a, 0));

            let inputTokenGateBalanceBefore = await inputToken.balanceOf(inputTokenStarkgate.address);
            let outputTokenGateBalanceBefore = await outputToken.balanceOf(outputTokenStarkgate.address);
            let inputTokenDeFiContractBalanceBefore = await inputToken.balanceOf(deFiContract.address);
            let outputTokenDeFiContractBalanceBefore = await outputToken.balanceOf(deFiContract.address);

            // Create token message and amount info messages that the L1Admiral will be able to consume
            await Promise.all(amounts.map(async amount => {
                // Token message
                await createStarkateTokenWithdrawalMessage(
                    starknetCore,
                    INPUT_TOKEN_L2_STARKGATE_ADDRESS,
                    inputTokenStarkgate.address,
                    l1Conductor.address,
                    amount
                );

                // Amount info message
                let payload: bigint[] = [];
                payload[0] = BigInt(amount) & (UINT256_PART_SIZE - 1n);
                payload[1] = BigInt(amount) >> UINT256_PART_SIZE_BITS;
                starknetCore.addL2ToL1Message(
                    BigInt(INPUT_TO_OUTPUT_L2_CONDUCTOR_ADDRESS),
                    BigInt(l1Conductor.address),
                    payload
                );
            }));

            await l1Conductor.executeRides(amounts);

            let inputTokenGateBalanceAfter = await inputToken.balanceOf(inputTokenStarkgate.address);
            let outputTokenGateBalanceAfter = await outputToken.balanceOf(outputTokenStarkgate.address);
            let inputTokenDeFiContractBalanceAfter = await inputToken.balanceOf(deFiContract.address);
            let outputTokenDeFiContractBalanceAfter = await outputToken.balanceOf(deFiContract.address);

            // inputTokenGateBalanceBefore - totalAmounts == inputTokenGateBalanceAfter
            expect(inputTokenGateBalanceBefore.sub(totalAmounts)).to.equal(inputTokenGateBalanceAfter);

            // outputTokenGateBalanceBefore + totalAmounts == outputTokenGateBalanceAfter
            expect(outputTokenGateBalanceBefore.add(totalAmounts)).to.equal(outputTokenGateBalanceAfter);

            // inputTokenDeFiContractBalanceBefore + totalAmounts == inputTokenDeFiContractBalanceAfter
            expect(inputTokenDeFiContractBalanceBefore.add(totalAmounts)).to.equal(inputTokenDeFiContractBalanceAfter);

            // outputTokenDeFiContractBalanceBefore - totalAmounts == outputTokenDeFiContractBalanceAfter
            expect(outputTokenDeFiContractBalanceBefore.sub(totalAmounts)).to.equal(outputTokenDeFiContractBalanceAfter);
        });
    });

    rideAmounts.forEach(async function(amounts) {
        it(
            `should pull tokens from starkgate but not execute rides if amount info messages were not sent.
            Then, after the amount info messages are sent, a subsequent call to executeRides() should execute
            the rides.`,
            async function () {

            let totalAmounts = ethers.BigNumber.from(amounts.reduce((partialSum, a) => partialSum + a, 0));

            let inputTokenGateBalanceBefore = await inputToken.balanceOf(inputTokenStarkgate.address);
            let outputTokenGateBalanceBefore = await outputToken.balanceOf(outputTokenStarkgate.address);
            let inputTokenDeFiContractBalanceBefore = await inputToken.balanceOf(deFiContract.address);
            let outputTokenDeFiContractBalanceBefore = await outputToken.balanceOf(deFiContract.address);
            let inputTokenL1AdmiralBalanceBefore = await inputToken.balanceOf(l1Conductor.address);

            // Create token message that the L1Admiral will be able to consume
            await Promise.all(amounts.map(async amount => {
                // Token message
                await createStarkateTokenWithdrawalMessage(
                    starknetCore,
                    INPUT_TOKEN_L2_STARKGATE_ADDRESS,
                    inputTokenStarkgate.address,
                    l1Conductor.address,
                    amount
                );
            }));

            await l1Conductor.executeRides(amounts);

            let inputTokenGateBalanceAfter = await inputToken.balanceOf(inputTokenStarkgate.address);
            let outputTokenGateBalanceAfter = await outputToken.balanceOf(outputTokenStarkgate.address);
            let inputTokenDeFiContractBalanceAfter = await inputToken.balanceOf(deFiContract.address);
            let outputTokenDeFiContractBalanceAfter = await outputToken.balanceOf(deFiContract.address);
            let inputTokenL1AdmiralBalanceAfter = await inputToken.balanceOf(l1Conductor.address);

            // inputTokenGateBalanceBefore - totalAmounts == inputTokenGateBalanceAfter
            expect(inputTokenGateBalanceBefore.sub(totalAmounts)).to.equal(inputTokenGateBalanceAfter);

            // outputTokenGateBalanceBefore == outputTokenGateBalanceAfter
            expect(outputTokenGateBalanceBefore).to.equal(outputTokenGateBalanceAfter);

            // inputTokenDeFiContractBalanceBefore == inputTokenDeFiContractBalanceAfter
            expect(inputTokenDeFiContractBalanceBefore).to.equal(inputTokenDeFiContractBalanceAfter);

            // outputTokenDeFiContractBalanceBefore == outputTokenDeFiContractBalanceAfter
            expect(outputTokenDeFiContractBalanceBefore).to.equal(outputTokenDeFiContractBalanceAfter);

            // inputTokenL1AdmiralBalanceBefore + totalAmounts == inputTokenL1AdmiralBalanceAfter
            expect(inputTokenL1AdmiralBalanceBefore.add(totalAmounts)).to.equal(inputTokenL1AdmiralBalanceAfter);

            // Send the amount info messages
            await Promise.all(amounts.map(async amount => {
                // Amount info message
                let payload: bigint[] = [];
                payload[0] = BigInt(amount) & (UINT256_PART_SIZE - 1n);
                payload[1] = BigInt(amount) >> UINT256_PART_SIZE_BITS;
                starknetCore.addL2ToL1Message(
                    BigInt(INPUT_TO_OUTPUT_L2_CONDUCTOR_ADDRESS),
                    BigInt(l1Conductor.address),
                    payload
                );
            }));

            await l1Conductor.executeRides(amounts);

            inputTokenGateBalanceAfter = await inputToken.balanceOf(inputTokenStarkgate.address);
            outputTokenGateBalanceAfter = await outputToken.balanceOf(outputTokenStarkgate.address);
            inputTokenDeFiContractBalanceAfter = await inputToken.balanceOf(deFiContract.address);
            outputTokenDeFiContractBalanceAfter = await outputToken.balanceOf(deFiContract.address);
            inputTokenL1AdmiralBalanceAfter = await inputToken.balanceOf(l1Conductor.address);

            // inputTokenGateBalanceBefore - totalAmounts == inputTokenGateBalanceAfter
            expect(inputTokenGateBalanceBefore.sub(totalAmounts)).to.equal(inputTokenGateBalanceAfter);

            // outputTokenGateBalanceBefore + totalAmounts == outputTokenGateBalanceAfter
            expect(outputTokenGateBalanceBefore.add(totalAmounts)).to.equal(outputTokenGateBalanceAfter);

            // inputTokenDeFiContractBalanceBefore + totalAmounts == inputTokenDeFiContractBalanceAfter
            expect(inputTokenDeFiContractBalanceBefore.add(totalAmounts)).to.equal(inputTokenDeFiContractBalanceAfter);

            // outputTokenDeFiContractBalanceBefore - totalAmounts == outputTokenDeFiContractBalanceAfter
            expect(outputTokenDeFiContractBalanceBefore.sub(totalAmounts)).to.equal(outputTokenDeFiContractBalanceAfter);

            // inputTokenL1AdmiralBalanceBefore == inputTokenL1AdmiralBalanceAfter
            expect(inputTokenL1AdmiralBalanceBefore).to.equal(inputTokenL1AdmiralBalanceAfter);
        });
    });

    rideAmounts.forEach(async function(amounts) {
        it(
            `should fail to execute rides if amount info messages are available, but no tokens were sent.
            It should subsequently succeed in executing the rides if the tokens were sent.`,
            async function () {

            let totalAmounts = ethers.BigNumber.from(amounts.reduce((partialSum, a) => partialSum + a, 0));

            let inputTokenGateBalanceBefore = await inputToken.balanceOf(inputTokenStarkgate.address);
            let outputTokenGateBalanceBefore = await outputToken.balanceOf(outputTokenStarkgate.address);
            let inputTokenDeFiContractBalanceBefore = await inputToken.balanceOf(deFiContract.address);
            let outputTokenDeFiContractBalanceBefore = await outputToken.balanceOf(deFiContract.address);
            let inputTokenL1AdmiralBalanceBefore = await inputToken.balanceOf(l1Conductor.address);

            // Create token message that the L1Admiral will be able to consume
            await Promise.all(amounts.map(async amount => {
                // Amount info message
                let payload: bigint[] = [];
                payload[0] = BigInt(amount) & (UINT256_PART_SIZE - 1n);
                payload[1] = BigInt(amount) >> UINT256_PART_SIZE_BITS;
                starknetCore.addL2ToL1Message(
                    BigInt(INPUT_TO_OUTPUT_L2_CONDUCTOR_ADDRESS),
                    BigInt(l1Conductor.address),
                    payload
                );
            }));

            await l1Conductor.executeRides(amounts);

            let inputTokenGateBalanceAfter = await inputToken.balanceOf(inputTokenStarkgate.address);
            let outputTokenGateBalanceAfter = await outputToken.balanceOf(outputTokenStarkgate.address);
            let inputTokenDeFiContractBalanceAfter = await inputToken.balanceOf(deFiContract.address);
            let outputTokenDeFiContractBalanceAfter = await outputToken.balanceOf(deFiContract.address);
            let inputTokenL1AdmiralBalanceAfter = await inputToken.balanceOf(l1Conductor.address);

            // inputTokenGateBalanceBefore == inputTokenGateBalanceAfter
            expect(inputTokenGateBalanceBefore).to.equal(inputTokenGateBalanceAfter);

            // outputTokenGateBalanceBefore == outputTokenGateBalanceAfter
            expect(outputTokenGateBalanceBefore).to.equal(outputTokenGateBalanceAfter);

            // inputTokenDeFiContractBalanceBefore == inputTokenDeFiContractBalanceAfter
            expect(inputTokenDeFiContractBalanceBefore).to.equal(inputTokenDeFiContractBalanceAfter);

            // outputTokenDeFiContractBalanceBefore == outputTokenDeFiContractBalanceAfter
            expect(outputTokenDeFiContractBalanceBefore).to.equal(outputTokenDeFiContractBalanceAfter);

            // inputTokenL1AdmiralBalanceBefore == inputTokenL1AdmiralBalanceAfter
            expect(inputTokenL1AdmiralBalanceBefore).to.equal(inputTokenL1AdmiralBalanceAfter);

            // Send the amount info messages
            await Promise.all(amounts.map(async amount => {
                // Token message
                await createStarkateTokenWithdrawalMessage(
                    starknetCore,
                    INPUT_TOKEN_L2_STARKGATE_ADDRESS,
                    inputTokenStarkgate.address,
                    l1Conductor.address,
                    amount
                );
            }));

            await l1Conductor.executeRides(amounts);

            inputTokenGateBalanceAfter = await inputToken.balanceOf(inputTokenStarkgate.address);
            outputTokenGateBalanceAfter = await outputToken.balanceOf(outputTokenStarkgate.address);
            inputTokenDeFiContractBalanceAfter = await inputToken.balanceOf(deFiContract.address);
            outputTokenDeFiContractBalanceAfter = await outputToken.balanceOf(deFiContract.address);
            inputTokenL1AdmiralBalanceAfter = await inputToken.balanceOf(l1Conductor.address);

            // inputTokenGateBalanceBefore - totalAmounts == inputTokenGateBalanceAfter
            expect(inputTokenGateBalanceBefore.sub(totalAmounts)).to.equal(inputTokenGateBalanceAfter);

            // outputTokenGateBalanceBefore + totalAmounts == outputTokenGateBalanceAfter
            expect(outputTokenGateBalanceBefore.add(totalAmounts)).to.equal(outputTokenGateBalanceAfter);

            // inputTokenDeFiContractBalanceBefore + totalAmounts == inputTokenDeFiContractBalanceAfter
            expect(inputTokenDeFiContractBalanceBefore.add(totalAmounts)).to.equal(inputTokenDeFiContractBalanceAfter);

            // outputTokenDeFiContractBalanceBefore - totalAmounts == outputTokenDeFiContractBalanceAfter
            expect(outputTokenDeFiContractBalanceBefore.sub(totalAmounts)).to.equal(outputTokenDeFiContractBalanceAfter);

            // inputTokenL1AdmiralBalanceBefore == inputTokenL1AdmiralBalanceAfter
            expect(inputTokenL1AdmiralBalanceBefore).to.equal(inputTokenL1AdmiralBalanceAfter);
        });
    });

    // it("should fail to execute when depositing to Starkgate fails", async function () {

    // });

    // it("should succeed in depositing to Starkgate even if Starkgate is not ERC-20 approved beforehand", async function () {

    // });

    // TODO: Test finalization message
});
