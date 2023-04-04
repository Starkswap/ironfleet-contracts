import asyncio
import os
from distutils.sysconfig import get_python_lib
from enum import Enum

import pytest
import pytest_asyncio
from starkware.starknet.testing.starknet import Starknet

from account import Account
from open_zeppelin.utils import (str_to_felt, uint)

ACCOUNT_FILE = os.path.join(get_python_lib(), "openzeppelin/account/presets/Account.cairo")
MINTABLE_TOKEN = os.path.join(get_python_lib(), "openzeppelin/token/erc20/presets/ERC20Mintable.cairo")
ADMIRAL_FILE = os.path.join(os.path.dirname(__file__), "../../../contracts/l2/L2Admiral.cairo")
MOCK_STARKGATE = os.path.join(os.path.dirname(__file__), "../../../contracts/l2/testing/MockStarkGate.cairo")

L1_CONTRACT_ADDRESS = 0x42


class ShipStatus(Enum):
    FINALISED = 0
    OPEN = 1
    AT_SEA = 2
    RETURNED = 3


@pytest_asyncio.fixture(scope="module")
async def starknet():
    return await Starknet.empty()


@pytest_asyncio.fixture(scope="module")
async def cargo_token(starknet, l2_keeper):
    cargo_token = await starknet.deploy(MINTABLE_TOKEN, constructor_calldata=[
        str_to_felt("PoolingToken"),
        str_to_felt("PT"),
        18,
        *uint(0),
        l2_keeper.contract_address,
        l2_keeper.contract_address
    ])

    return cargo_token


@pytest_asyncio.fixture(scope="module")
async def loot_token(starknet, l2_keeper):
    loot_token = await starknet.deploy(MINTABLE_TOKEN, constructor_calldata=[
        str_to_felt("PayoutToken"),
        str_to_felt("RT"),
        18,
        *uint(0),
        l2_keeper.contract_address,
        l2_keeper.contract_address
    ])
    return loot_token


@pytest_asyncio.fixture(scope="function")
async def starkgate(starknet):
    starkgate = await starknet.deploy(MOCK_STARKGATE, constructor_calldata=[0])
    return starkgate


@pytest_asyncio.fixture(scope="function")
async def admiral(starknet, starkgate, cargo_token, loot_token, l2_keeper):
    admiral = await starknet.deploy(ADMIRAL_FILE, constructor_calldata=[
        starkgate.contract_address,
        cargo_token.contract_address,
        loot_token.contract_address,
        l2_keeper.contract_address
    ])

    await l2_keeper.send_transaction(admiral.contract_address, 'set_l1_conductor_address',
                                     calldata=[L1_CONTRACT_ADDRESS])
    return admiral


async def deploy_account(starknet):
    u = Account(123456789987654321)
    u.set_contract(await starknet.deploy(ACCOUNT_FILE, constructor_calldata=[u.public_key]))
    return u


@pytest_asyncio.fixture(scope="module")
async def l2_keeper(starknet):
    return await deploy_account(starknet)


@pytest_asyncio.fixture(scope="function")
async def user1(starknet):
    return await deploy_account(starknet)


@pytest_asyncio.fixture(scope="function")
async def user2(starknet):
    return await deploy_account(starknet)


@pytest_asyncio.fixture(scope="function")
async def user3(starknet):
    return await deploy_account(starknet)


@pytest.fixture(scope='module')
def event_loop(request):
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
